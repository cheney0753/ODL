﻿# Copyright 2014-2016 The ODL development group
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

"""Utilities for normalization of user input."""

# Imports for common Python 2/3 codebase
from __future__ import print_function, division, absolute_import
from future import standard_library
standard_library.install_aliases()
from future.utils import raise_from

import numpy as np


__all__ = ('normalized_index_expression', 'normalized_scalar_param_list')


def normalized_scalar_param_list(param, length, param_conv=None,
                                 keep_none=True):
    """Return a list of given length from a scalar parameter.

    The typical use case is when a single value or a sequence of
    values is accepted as input. This function makes a list from
    a given sequence or a list of identical elements from a single
    value, with cast to a given parameter type if desired.

    To distinguish a parameter sequence from a single parameter, the
    following rules are applied:

    * If ``param`` is not a sequence, it is treated as a single
    parameter (e.g. ``1``).
    * If ``len(param) == length == 1``, then ``param`` is interpreted
      as a single parameter (e.g. ``[1]`` or ``'1'``).
    * If ``len(param) == length != 1``, then ``param`` is interpreted as
      sequence of parameters.
    * Otherwise, ``param`` is interpreted as a single parameter.

    Note that this function is not applicable to parameters which are
    themselves iterable (e.g. ``'abc'`` with ``length=3`` will be
    interpreted as equivalent to ``['a', 'b', 'c']``).

    Parameters
    ----------
    param :
        Input parameter to turn into a list.
    length : positive int
        Desired length of the output list.
    param_conv : callable, optional
        Conversion applied to each list element. None means no conversion.
    keep_none : bool, optional
        If True, None is not converted.

    Returns
    -------
    plist : list
        Input parameter turned into a list of length ``length``.

    Examples
    --------
    Turn input into a list of given length, possibly by broadcasting.
    By default, no conversion is performed.

    >>> normalized_scalar_param_list((1, 2, 3), 3)
    [1, 2, 3]
    >>> normalized_scalar_param_list((1, None, 3.0), 3)
    [1, None, 3.0]

    Single parameters are broadcast to the given length.

    >>> normalized_scalar_param_list(1, 3)
    [1, 1, 1]
    >>> normalized_scalar_param_list('10', 3)
    ['10', '10', '10']
    >>> normalized_scalar_param_list(None, 3)
    [None, None, None]

    List entries can be explicitly converted using ``param_conv``. If
    ``None`` should be kept, set ``keep_none`` to True:

    >>> normalized_scalar_param_list(1, 3, param_conv=float)
    [1.0, 1.0, 1.0]
    >>> normalized_scalar_param_list('10', 3, param_conv=int)
    [10, 10, 10]
    >>> normalized_scalar_param_list((1, None, 3.0), 3, param_conv=int,
    ...                              keep_none=True)  # default
    [1, None, 3]

    The conversion parameter can be any callable:

    >>> def myconv(x):
    ...     return False if x is None else bool(x)
    >>> normalized_scalar_param_list((0, None, 3.0), 3, param_conv=myconv,
    ...                              keep_none=False)
    [False, False, True]
    """
    length, length_in = int(length), length
    if length <= 0:
        raise ValueError('`length` must be positive, got {}'.format(length_in))

    try:
        # TODO: always use this when numpy >= 1.10 can be assumed
        param = np.array(param, dtype=object, copy=True, ndmin=1)
        out_list = list(np.broadcast_to(param, (length,)))
    except AttributeError:
        # numpy.broadcast_to not available
        if np.isscalar(param):
            # Try this first, will work better with iterable input like '10'
            out_list = [param] * length
        else:
            try:
                param_len = len(param)
            except TypeError:
                # Not a sequence -> single parameter
                out_list = [param] * length
            else:
                if param_len == 1:
                    out_list = list(param) * length
                elif param_len == length:
                    out_list = list(param)
                else:
                    raise ValueError('sequence `param` has length {}, '
                                     'expected {}'.format(param_len, length))

    if len(out_list) != length:
        raise ValueError('sequence `param` has length {}, expected {}'
                         ''.format(len(out_list), length))

    if param_conv is not None:
        for i, p in enumerate(out_list):
            if p is None and keep_none:
                pass
            else:
                out_list[i] = param_conv(p)

    return out_list


def normalized_index_expression(indices, shape, int_to_slice=False):
    """Enable indexing with almost Numpy-like capabilities.

    Implements the following features:

    - Usage of general slices and sequences of slices
    - Conversion of `Ellipsis` into an adequate number of ``slice(None)``
      objects
    - Fewer indices than axes by filling up with an `Ellipsis`
    - Error checking with respect to a given shape
    - Conversion of integer indices into corresponding slices

    Parameters
    ----------
    indices : int, slice, Ellipsis or sequence of these
        Index expression to be normalized
    shape : sequence of int
        Target shape for error checking of out-of-bounds indices.
        Also needed to determine the number of axes.
    int_to_slice : bool, optional
        If True, turn integers into corresponding slice objects.

    Returns
    -------
    normalized : tuple of int or slice
        Normalized index expression

    Examples
    --------
    Sequences are turned into tuples. We can have at most as many entries
    as the length of ``shape``, but fewer are allowed - the remaining
    list places are filled up by ``slice(None)``:

    >>> normalized_index_expression([1, 2, 3], shape=(3, 4, 5))
    (1, 2, 3)
    >>> normalized_index_expression([1, 2], shape=(3, 4, 5))
    (1, 2, slice(None, None, None))
    >>> normalized_index_expression([slice(2), 2], shape=(3, 4, 5))
    (slice(None, 2, None), 2, slice(None, None, None))
    >>> normalized_index_expression([1, Ellipsis], shape=(3, 4, 5))
    (1, slice(None, None, None), slice(None, None, None))

    By default, integer indices are kept. If they should be converted
    to slices, use ``int_to_slice=True``. This can be useful to guarantee
    that the result of slicing with the returned object is of the same
    type as the array into which is sliced and has the same number of
    axes:

    >>> x = np.zeros(shape=(3, 4, 5))
    >>> idx1 = normalized_index_expression([1, 2, 3], shape=(3, 4, 5),
    ...                                   int_to_slice=True)
    >>> idx1
    (slice(1, 2, None), slice(2, 3, None), slice(3, 4, None))
    >>> x[idx1]
    array([[[ 0.]]])
    >>> x[idx1].shape
    (1, 1, 1)
    >>> idx2 = normalized_index_expression([1, 2, 3], shape=(3, 4, 5),
    ...                                   int_to_slice=False)
    >>> idx2
    (1, 2, 3)
    >>> x[idx2]
    0.0
    """
    ndim = len(shape)
    # Support indexing with fewer indices as indexing along the first
    # corresponding axes. In the other cases, normalize the input.
    if np.isscalar(indices):
        indices = [indices, Ellipsis]
    elif (isinstance(indices, slice) or indices is Ellipsis):
        indices = [indices]

    indices = list(indices)
    if len(indices) < ndim and Ellipsis not in indices:
        indices.append(Ellipsis)

    # Turn Ellipsis into the correct number of slice(None)
    if Ellipsis in indices:
        if indices.count(Ellipsis) > 1:
            raise ValueError('cannot use more than one Ellipsis.')

        eidx = indices.index(Ellipsis)
        extra_dims = ndim - len(indices) + 1
        indices = (indices[:eidx] + [slice(None)] * extra_dims +
                   indices[eidx + 1:])

    # Turn single indices into length-1 slices if desired
    for (i, idx), n in zip(enumerate(indices), shape):
        if np.isscalar(idx):
            if idx < 0:
                idx += n

            if idx >= n:
                raise IndexError('Index {} is out of bounds for axis '
                                 '{} with size {}.'
                                 ''.format(idx, i, n))
            if int_to_slice:
                indices[i] = slice(idx, idx + 1)

    # Catch most common errors
    if any(s.start == s.stop and s.start is not None or
           s.start == n
           for s, n in zip(indices, shape) if isinstance(s, slice)):
        raise ValueError('Slices with empty axes not allowed.')
    if None in indices:
        raise ValueError('creating new axes is not supported.')
    if len(indices) > ndim:
        raise IndexError('too may indices: {} > {}.'
                         ''.format(len(indices), ndim))

    return tuple(indices)


if __name__ == '__main__':
    # pylint: disable=wrong-import-position
    from odl.util.testutils import run_doctests
    run_doctests()