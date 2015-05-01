# Copyright 2014, 2015 Holger Kohr, Jonas Adler
#
# This file is part of RL.
#
# RL is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# RL is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with RL.  If not, see <http://www.gnu.org/licenses/>.


# Imports for common Python 2/3 codebase
from __future__ import unicode_literals, print_function, division
from __future__ import absolute_import
try:
    from builtins import str
except ImportError:  # Versions < 0.14 of python-future
    from future.builtins import str
from future import standard_library

# External module imports
import numpy as np

# RL imports
import RL.operator.function as fun
import RL.space.space as spaces
import RL.space.set as sets
import RLcpp.PyCuda

standard_library.install_aliases()


class CudaRN(spaces.HilbertSpace, spaces.Algebra):
    """The real space R^n
    """

    def __init__(self, n):
        self.n = n
        self._field = sets.RealNumbers()
        self.impl = RLcpp.PyCuda.CudaRNImpl(n)

    def innerImpl(self, x, y):
        return self.impl.inner(x.impl, y.impl)

    def normSqImpl(self, x):  # Optimized separately from inner
        return self.impl.normSq(x.impl)

    def linCombImpl(self, z, a, x, b, y):
        self.impl.linComb(z.impl, a, x.impl, b, y.impl)

    def multiplyImpl(self, x, y):
        self.impl.multiply(x.impl, y.impl)

    def zero(self):
        return self.makeVector(self.impl.zero())

    def empty(self):
        return self.makeVector(self.impl.empty())

    @property
    def field(self):
        return self._field

    @property
    def dimension(self):
        return self.n

    def equals(self, other):
        return isinstance(other, CudaRN) and self.n == other.n

    def makeVector(self, *args, **kwargs):
        return CudaRN.Vector(self, *args, **kwargs)

    def __str__(self):
        return "CudaRN(" + str(self.n) + ")"

    @property
    def abs(self):
        return fun.LambdaFunction(
            lambda input, output: RLcpp.PyCuda.abs(input.impl, output.impl),
            (self, self))

    @property
    def sign(self):
        return fun.LambdaFunction(
            lambda input, output: RLcpp.PyCuda.sign(input.impl, output.impl),
            input=(self, self))

    @property
    def addScalar(self):
        return fun.LambdaFunction(
            lambda input, scalar,
            output: RLcpp.PyCuda.addScalar(input.impl, scalar, output.impl),
            input=(self, self.field, self))

    @property
    def maxVectorScalar(self):
        return fun.LambdaFunction(
            lambda input, scalar,
            output: RLcpp.PyCuda.maxVectorScalar(input.impl, scalar,
                                                 output.impl),
            input=(self, self.field, self))

    @property
    def maxVectorVector(self):
        return fun.LambdaFunction(
            lambda input1, input2,
            output: RLcpp.PyCuda.maxVectorVector(input1.impl, input2.impl,
                                                 output.impl),
            input=(self, self, self))

    @property
    def sum(self):
        return fun.LambdaFunction(
            lambda input, output: RLcpp.PyCuda.abs(input.impl),
            input=(self), returns=self.field)

    class Vector(spaces.HilbertSpace.Vector, spaces.Algebra.Vector):
        def __init__(self, space, *args):
            spaces.HilbertSpace.Vector.__init__(self, space)
            if isinstance(args[0], RLcpp.PyCuda.CudaRNVectorImpl):
                self.impl = args[0]
            elif isinstance(args[0], np.ndarray):
                self.impl = space.impl.empty()
                self[:] = args[0]
            elif isinstance(args[0], list):
                self.impl = space.impl.empty()
                self[:] = np.array(args[0], dtype=np.float)
            else:
                self.impl = RLcpp.PyCuda.CudaRNVectorImpl(*args)

        def __str__(self):
            return (self.space.__str__() + '::Vector(' + self[:].__str__() +
                    ')')

        def __repr__(self):
            return (self.space.__repr__() + '::Vector(' + self[:].__repr__() +
                    ')')

        # Slow get and set, for testing and nothing else!
        def __getitem__(self, index):
            if isinstance(index, slice):
                return self.impl.getSlice(index)
            else:
                return self.impl.__getitem__(index)

        def __setitem__(self, index, value):
            if isinstance(index, slice):
                # Convert value to the correct type
                if not isinstance(value, np.ndarray):
                    value = np.array(value, dtype=np.float)
                elif value.dtype.type is not np.float:
                    value = value.astype(np.float)

                self.impl.setSlice(index, value)
            else:
                self.impl.__setitem__(index, value)
