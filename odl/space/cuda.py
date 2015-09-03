# Copyright 2014, 2015 The ODL development group
#
# This file is part of ODL.
#
# ODL is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ODL is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ODL.  If not, see <http://www.gnu.org/licenses/>.

"""CUDA implementation of n-dimensional Cartesian spaces.

# TODO: document public interface
"""

# Imports for common Python 2/3 codebase
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)
from builtins import str, super
from future import standard_library

# External module imports
import numpy as np
from numbers import Integral

# ODL imports
import odl.space.space as spaces
import odl.space.set as sets
from odl.utility.utility import errfmt, array1d_repr, dtype_repr
import odlpp.odlpp_cuda as cuda

standard_library.install_aliases()

def _get_int_type():
    if np.dtype(np.int).itemsize == 4:
        return cuda.CudaVectorInt32
    elif np.dtype(np.int).itemsize == 8:
        return cuda.CudaVectorInt64
    else:
        raise NotImplementedError("int size not implemented")

class CudaFn(spaces.LinearSpace):

    """The real space E^n, implemented in CUDA.

    Requires the compiled ODL extension odlpp.

    # TODO: document public interface
    """

    dtypes = {np.dtype(np.float): cuda.CudaVectorFloat64,
              np.dtype(np.float32): cuda.CudaVectorFloat32,
              np.dtype(np.float64): cuda.CudaVectorFloat64,
              np.dtype(np.int): _get_int_type(),
              np.dtype(np.int8): cuda.CudaVectorInt8,
              np.dtype(np.int16): cuda.CudaVectorInt16,
              np.dtype(np.int32): cuda.CudaVectorInt32,
              np.dtype(np.int64): cuda.CudaVectorInt64,
              np.dtype(np.uint8): cuda.CudaVectorUInt8,
              np.dtype(np.uint16): cuda.CudaVectorUInt16,
              np.dtype(np.uint32): cuda.CudaVectorUInt32,
              np.dtype(np.uint64): cuda.CudaVectorUInt64}


    def __init__(self, dim, dtype=np.float32):
        """Initialize a new CudaFn.

        Parameters
        ----------

        dim : int
            The dimension of the space

        dtype : type
            Numpy data type mapped to a CudaVector data type.
            Currently supported:
            float32, uint8
        """
        if not isinstance(dim, Integral) or dim < 1:
            raise TypeError(errfmt('''
            dim ({}) has to be a positive integer'''.format(dim)))
        
        self._field = sets.RealNumbers()
        self._dim = dim
        self._dtype = np.dtype(dtype)
        self._vector_impl = self.dtypes.get(self._dtype)
        if self._vector_impl is None:
            raise TypeError(errfmt('''
            dtype ({}) must be a valid CudaFn.dtype'''.format(dtype)))

    def element(self, inp=None, data_ptr=None):
        """Create an element from given data or from scratch.

        TODO: write up properly

        Parameters
        ----------
        inp : array-like, optional

        The method has two call patterns, the first is:

        *args : numpy.ndarray
            Array that will be copied to the GPU.
            Data is not modified or bound.
            The shape of the array must be (n,)

        **kwargs : None

        The second pattern is to create a new numpy array which will then
        be copied to the GPU. In this case

        *args : Options for numpy.array constructor
        **kwargs : Options for numpy.array constructor

        Returns
        -------
        CudaFn.Vector instance


        Examples
        --------

        >>> rn = CudaFn(3)
        >>> x = rn.element(np.array([1, 2, 3]))
        >>> x
        CudaFn(3).element([1.0, 2.0, 3.0])
        >>> y = rn.element([1, 2, 3])
        >>> y
        CudaFn(3).element([1.0, 2.0, 3.0])

        """
        if inp is None and data_ptr is None:
            return self.Vector(self, self._vector_impl(self.dim))
        elif inp is None:
            return self.Vector(
                self, self._vector_impl.from_pointer(data_ptr, self.dim))
        elif data_ptr is None:
            elem = self.element()
            elem[:] = inp
            return elem
        else:
            raise TypeError("Cannot provide both inp and data_ptr")

    def _lincomb(self, z, a, x, b, y):
        """Linear combination of `x` and `y`.

        Calculates z = a*x + b*y

        Parameters
        ----------
        z : CudaFn.Vector
            The Vector that the result should be written to.
        a : RealNumber
            Scalar to multiply `x` with.
        x : CudaFn.Vector
            The first summand
        b : RealNumber
            Scalar to multiply `y` with.
        y : CudaFn.Vector
            The second summand

        Returns
        -------
        None

        Examples
        --------
        >>> rn = CudaFn(3)
        >>> x = rn.element([1, 2, 3])
        >>> y = rn.element([4, 5, 6])
        >>> z = rn.element()
        >>> rn.lincomb(z, 2, x, 3, y)
        >>> z
        CudaFn(3).element([14.0, 19.0, 24.0])
        """
        z.data.linComb(a, x.data, b, y.data)

    def zero(self):
        """Create a vector of zeros.

        Parameters
        ----------
        None

        Returns
        -------
        CudaFn.Vector instance with all elements set to zero (0.0)


        Examples
        --------

        >>> rn = CudaFn(3)
        >>> y = rn.zero()
        >>> y
        CudaFn(3).element([0.0, 0.0, 0.0])
        """
        return self.Vector(self, self._vector_impl(self.dim, 0))

    @property
    def field(self):
        """The underlying field of R^n is the set of real numbers.

        Parameters
        ----------
        None

        Returns
        -------
        RealNumbers instance


        Examples
        --------

        >>> rn = CudaFn(3, np.float32)
        >>> rn.field
        RealNumbers()
        """
        return self._field

    @property
    def dim(self):
        """The dimension of this space.

        Parameters
        ----------
        None

        Returns
        -------
        Integer


        Examples
        --------

        >>> rn = CudaFn(3)
        >>> rn.dim
        3
        """
        return self._dim

    def equals(self, other):
        """Check if `other` is a CudaFn instance of the same dimension.

        Parameters
        ----------
        other : any object
            The object to check for equality

        Returns
        -------
        eq : boolean
            True if equal, else false

        Examples
        --------
        Comparing with self:

        >>> r3 = CudaFn(3)
        >>> r3.equals(r3)
        True
        >>> r3a, r3b = CudaFn(3), CudaFn(3)
        >>> r3a.equals(r3b)
        True

        False when comparing to other dimension Rn:

        >>> r3, r4 = CudaFn(3), CudaFn(4)
        >>> r3.equals(r4)
        False

        We also support operators '==' and '!=':

        >>> r3, r4 = CudaFn(3), CudaFn(4)
        >>> r3 == r3
        True
        >>> r3 == r4
        False
        >>> r3 != r4
        True
        """
        return (type(self) == type(other) and
                self.dim == other.dim and
                self._dtype == other._dtype)

    def __str__(self):
        """str() implementation."""
        return "CudaFn(" + str(self.dim) + ")"

    def __repr__(self):
        """repr() implementation."""
        if self._dtype == np.float32:
            return "CudaFn(" + str(self.dim) + ")"
        else:
            return "CudaFn(" + str(self.dim) + ', ' + dtype_repr(self._dtype) + ')'

    class Vector(spaces.LinearSpace.Vector):

        """An E^n vector represented in CUDA.

        # TODO: document public interface
        """

        def __init__(self, space, data):
            """Initialize a new CudaFn vector.

            Parameters
            ----------

            space : CudaFn
                Instance of CudaFn this vector lives in
            data : CudaVectorFloat
                Underlying data-representation to be used by this vector
            """
            super().__init__(space)

            if not isinstance(data, self.space._vector_impl):
                return TypeError(errfmt('''
                'data' ({}) must be a CudaFnVectorImpl instance
                '''.format(data)))

            self._data = data

        @property
        def data(self):
            """The data of this vector.

            Parameters
            ----------
            None

            Returns
            -------
            ptr : CudaFnVectorImpl
                Underlying cuda data representation

            Examples
            --------
            """
            return self._data

        @property
        def data_ptr(self):
            """A raw pointer to the data of this vector.

            Parameters
            ----------
            None

            Returns
            -------
            ptr : Int
                Pointer to the CUDA data of this vector


            Examples
            --------

            >>> Zn = CudaFn(3, int)
            >>> x = Zn.element([1, 2, 3])
            >>> x
            CudaFn(3, int).element([1, 2, 3])
            >>> y = Zn.element(data_ptr=x.data_ptr)
            >>> y
            CudaFn(3, int).element([1, 2, 3])

            In-place modification via pointer:

            >>> y[0] = 5
            >>> x
            CudaFn(3, int).element([5, 2, 3])
            """
            return self._data.data_ptr()

        @property
        def itemsize(self):
            """The size in bytes of the underlying element type.

            Parameters
            ----------
            None

            Returns
            -------
            itemsize : Int
                Size in bytes of type
            """
            return self.space._dtype.itemsize  # Currently hardcoded to float

        def __str__(self):
            return str(self[:])

        def __repr__(self):
            """repr() implementation.

            Examples
            --------

            >>> rn = CudaFn(3)
            >>> x = rn.element([1, 2, 3])
            >>> y = eval(repr(x))
            >>> y
            CudaFn(3).element([1.0, 2.0, 3.0])
            >>> z = CudaFn(8).element([1, 2, 3, 4, 5, 6, 7, 8])
            >>> z
            CudaFn(8).element([1.0, 2.0, 3.0, ..., 6.0, 7.0, 8.0])
            """
            return '{!r}.element({})'.format(self.space, array1d_repr(self))

        def __len__(self):
            """The dimension of the underlying space."""
            return self.space.dim

        def __getitem__(self, index):
            """Access values of this vector.

            This will cause the values to be copied to CPU
            which is a slow operation.

            Parameters
            ----------

            index : int or slice
                The position(s) that should be accessed

            Returns
            -------
            If index is an `int`
            float, value at index

            If index is an `slice`
            numpy.ndarray instance with the values at the slice


            Examples
            --------

            >>> rn = CudaFn(3)
            >>> y = rn.element([1, 2, 3])
            >>> y[0]
            1.0
            >>> y[1:2]
            array([ 2.], dtype=float32)

            """
            if isinstance(index, slice):
                return self.data.getslice(index)
            else:
                return self.data.__getitem__(index)

        def __setitem__(self, index, value):
            """Set values of this vector.

            This will cause the values to be copied to CPU
            which is a slow operation.

            Parameters
            ----------

            index : int or slice
                The position(s) that should be set
            value : Real or array-like
                The values that should be assigned.

                If index is an integer, value should be a Number
                convertible to float.
                If index is a slice, value should be array-like of
                the same size as the slice.

            Returns
            -------
            None


            Examples
            --------

            >>> rn = CudaFn(3)
            >>> y = rn.element([1, 2, 3])
            >>> y[0] = 5
            >>> y
            CudaFn(3).element([5.0, 2.0, 3.0])
            >>> y[1:3] = [7, 8]
            >>> y
            CudaFn(3).element([5.0, 7.0, 8.0])
            >>> y[:] = np.array([0, 0, 0])
            >>> y
            CudaFn(3).element([0.0, 0.0, 0.0])
            
            """
            if isinstance(index, slice):
                # Convert value to the correct type if needed
                value = np.asarray(value, dtype=self.space._dtype)

                # Size checking is performed in c++
                self.data.setslice(index, value)
            else:
                self.data.__setitem__(index, value)


class CudaRn(CudaFn):

    """The real space :math:`R^n`, implemented in CUDA.

    Requires the compiled ODL extension odlpp.

    # TODO: document public interface
    """

    def __init__(self, dim):
        """Initialize a new CudaRn.

        Parameters
        ----------

        dim : int
            The dimension of the space
        """
        super().__init__(dim, np.float32)

    def _inner(self, x, y):
        """Calculate the inner product of x and y.

        Parameters
        ----------
        x : CudaRn.Vector
        y : CudaRn.Vector

        Returns
        -------
        inner: float
            The inner product of x and y


        Examples
        --------

        >>> rn = CudaRn(3)
        >>> x = rn.element([1, 2, 3])
        >>> y = rn.element([3, 1, 5])
        >>> rn.inner(x, y)
        20.0
        """
        return x.data.inner(y.data)

    def _norm(self, x):
        """Calculate the 2-norm of x.

        This method is implemented separately from `sqrt(inner(x,x))`
        for efficiency reasons.

        Parameters
        ----------
        x : CudaRn.Vector

        Returns
        -------
        norm : float
            The 2-norm of x


        Examples
        --------

        >>> rn = CudaRn(3)
        >>> x = rn.element([2, 3, 6])
        >>> rn.norm(x)
        7.0
        """
        return x.data.norm()

    def _multiply(self, z, x, y):
        """The pointwise product of two vectors, assigned to `y`.

        This is defined as:

        multiply(z, x, y) := [x[0]*y[0], x[1]*y[1], ..., x[n-1]*y[n-1]]

        Parameters
        ----------

        z : CudaRn.Vector
            Write to
        x : CudaRn.Vector
            Read from
        y : CudaRn.Vector
            Read from

        Returns
        -------
        None

        Examples
        --------

        >>> rn = CudaRn(3)
        >>> x = rn.element([5, 3, 2])
        >>> y = rn.element([1, 2, 3])
        >>> z = rn.element()
        >>> rn.multiply(z, x, y)
        >>> z
        CudaRn(3).element([5.0, 6.0, 6.0])
        """
        z.data.multiply(x.data, y.data)

    def __str__(self):
        """str() implementation."""
        return "CudaRn(" + str(self.dim) + ")"

    def __repr__(self):
        """repr() implementation."""
        return "CudaRn(" + str(self.dim) + ")"

    class Vector(CudaFn.Vector):
        pass


# Methods
# TODO: move
def abs(inp, outp):
    cuda.abs(inp.data, outp.data)


def sign(inp, outp):
    cuda.sign(inp.data, outp.data)


def add_scalar(inp, scal, outp):
    cuda.add_scalar(inp.data, scal, outp.data)


def max_vector_scalar(inp, scal, outp):
    cuda.max_vector_scalar(inp.data, scal, outp.data)


def max_vector_vector(inp1, inp2, outp):
    cuda.max_vector_vector(inp1.data, inp2.data, outp.data)


def sum(inp):
    return cuda.sum(inp.data)


try:
    CudaRn(1).element()
except MemoryError:
    raise ImportError(errfmt("""
                             Warning: Your GPU seems to be misconfigured. Skipping CUDA-dependent
                             modules."""))


if __name__ == '__main__':
    from doctest import testmod, NORMALIZE_WHITESPACE
    testmod(optionflags=NORMALIZE_WHITESPACE)
