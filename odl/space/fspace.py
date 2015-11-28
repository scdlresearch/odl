﻿# Copyright 2014, 2015 The ODL development group
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

"""Spaces of functions with common domain and range."""

# Imports for common Python 2/3 codebase
from __future__ import print_function, division, absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import str, super

# External imports
import numpy as np

# ODL imports
from odl.operator.operator import Operator
from odl.set.domain import IntervalProd
from odl.set.sets import RealNumbers, ComplexNumbers, Set
from odl.set.space import LinearSpace


__all__ = ('FunctionSet', 'FunctionSpace')


class FunctionSet(Set):
    """A general set of functions with common domain and range."""

    def __init__(self, dom, ran):
        """Initialize a new instance.

        Parameters
        ----------
        dom : :class:`~odl.Set`
            The domain of the functions.
        ran : :class:`~odl.Set`
            The range of the functions.
        """
        if not isinstance(dom, Set):
            raise TypeError('domain {!r} not a `Set` instance.'.format(dom))

        if not isinstance(ran, Set):
            raise TypeError('range {!r} not a `Set` instance.'.format(dom))

        self._domain = dom
        self._range = ran

    @property
    def domain(self):
        """Return domain attribute."""
        return self._domain

    @property
    def range(self):
        """Return range attribute."""
        return self._range

    def element(self, fcall=None, fapply=None):
        """Create a :class:`FunctionSet` element.

        Parameters
        ----------
        fcall : `callable`, optional
            The actual instruction for out-of-place evaluation.
            It must return an :attr:`range` element or a
            `numpy.ndarray` of such (vectorized call).

            If fcall is a :class:`FunctionSet.Vector`, it is wrapped
            as a new :class:`FunctionSet.Vector`.

        Returns
        -------
        element : :class:`FunctionSet.Vector`
            The new element created
        """
        if isinstance(fcall, self.Vector):  # no double wrapping
            return self.element(fcall._call)
        else:
            return self.Vector(self, fcall)

    def __eq__(self, other):
        """``s.__eq__(other) <==> s == other``.

        Returns
        -------
        equals : `bool`
            `True` if ``other`` is a :class:`FunctionSet` with same
            :attr:`FunctionSet.domain` and :attr:`FunctionSet.range`,
            `False` otherwise.
        """
        if other is self:
            return True

        return (isinstance(other, FunctionSet) and
                self.domain == other.domain and
                self.range == other.range)

    def __contains__(self, other):
        """``s.__contains__(other) <==> other in s``.

        Returns
        -------
        equals : `bool`
            `True` if ``other`` is a :class:`FunctionSet.Vector`
            whose :attr:`FunctionSet.Vector.space` attribute
            equals this space, `False` otherwise.
        """
        return (isinstance(other, FunctionSet.Vector) and
                self == other.space)

    def __repr__(self):
        """``s.__repr__() <==> repr(s)``."""
        return 'FunctionSet({!r}, {!r})'.format(self.domain, self.range)

    def __str__(self):
        """``s.__str__() <==> str(s)``."""
        return 'FunctionSet({}, {})'.format(self.domain, self.range)

    class Vector(Operator):

        """Representation of a :class:`FunctionSet` element."""

        def __init__(self, fset, fcall):
            """Initialize a new instance.

            Parameters
            ----------
            fset : :class:`FunctionSet`
                The set of functions this element lives in
            fcall : `callable`
                The actual instruction for out-of-place evaluation.
                It must return an :attr:`FunctionSet.range` element or a
                `numpy.ndarray` of such (vectorized call).

            *At least one of the arguments fcall and fapply` must
            be provided.*
            """
            if not isinstance(fset, FunctionSet):
                raise TypeError('function set {} not a :class:`FunctionSet` '
                                'instance.'.format(fset))

            if fcall is not None and not callable(fcall):
                raise TypeError('call function {} is not callable.'
                                ''.format(fcall))

            self._space = fset
            self._call_impl = fcall

            # Todo: allow users to specify linear
            super().__init__(self.space.domain, self.space.range, linear=False)

        @property
        def space(self):
            """Return space attribute."""
            return self._space

        def _call(self, x):
            return self._call_impl(*x)

        def __eq__(self, other):
            """``vec.__eq__(other) <==> vec == other``.

            Returns
            -------
            equals : `bool`
                `True` if ``other`` is a :class:`FunctionSet.Vector` with
                ``other.space`` equal to this vector's space and
                the call and apply implementations of ``other`` and
                this vector are equal. `False` otherwise.
            """
            if other is self:
                return True

            return (isinstance(other, FunctionSet.Vector) and
                    self.space == other.space and
                    self._call_imp == other._call_impl)

        # FIXME: this is a bad hack bypassing the operator default
        # pattern for apply and call
        def __call__(self, *x):
            """Vectorized and multi-argument out-of-place evaluation.

            Parameters
            ----------
            x1,...,xN : `object`
                Input arguments for the function evaluation.

            Returns
            -------
            out : :attr:`FunctionSet.range` element or array of elements
                Result of the function evaluation.
            """
            if x in self.domain:
                # single value list: f(0, 1, 2)
                pass
            elif x[0] in self.domain:
                # single array: f([0, 1, 2])
                pass
            else:  # Try vectorization
                if not isinstance(self.domain, IntervalProd):
                    raise TypeError('vectorized evaluation only possible for '
                                    '`IntervalProd` domains.')
                # Vectorization only allowed in this case

                # First case: (N, d) array of points, where d = dimension
                if (isinstance(x[0], np.ndarray) and
                        x[0].ndim == 2 and
                        x[0].shape[1] == self.domain.ndim):
                    min_coords = np.min(x[0], axis=0)
                    max_coords = np.max(x[0], axis=0)

                # Second case: d meshgrid type arrays
                elif (len(x) == self.domain.ndim and
                      all(isinstance(vec, np.ndarray) for vec in x)):
                    min_coords = [np.min(vec) for vec in x]
                    max_coords = [np.max(vec) for vec in x]

                else:
                    raise TypeError('input is neither an element of the '
                                    'function domain {} nor an array or '
                                    'meshgrid-type coordinate list.'
                                    ''.format(self.domain))

                if (min_coords not in self.domain or
                        max_coords not in self.domain):
                    raise ValueError('input contains points outside '
                                     '`domain` {}.'.format(self.domain))

            out = self._call(*x)

            if not (out in self.range or
                    (isinstance(out, np.ndarray) and
                     out.flat[0] in self.range)):
                raise TypeError('result {!r} not an element or an array of '
                                'elements of the function range {}.'
                                ''.format(out, self.range))

            return out

        def __ne__(self, other):
            """``vec.__ne__(other) <==> vec != other``"""
            return not self.__eq__(other)

        def __str__(self):
            """``vec.__str__() <==> str(vec)``"""
            if self._call is not None:
                return str(self._call)
            else:
                return str(self._apply_impl)

        def __repr__(self):
            """``vec.__repr__() <==> repr(vec)``"""
            if self._call is not None:
                return '{!r}.element({!r})'.format(self.space, self._call)
            else:
                return '{!r}.element({!r})'.format(self.space,
                                                   self._apply_impl)


class FunctionSpace(FunctionSet, LinearSpace):
    """A vector space of functions."""

    def __init__(self, dom, field=RealNumbers()):
        """Initialize a new instance.

        Parameters
        ----------
        dom : :class:`~odl.Set`
            The domain of the functions.
        field : :class:`~odl.RealNumbers` or :class:`~odl.ComplexNumbers`
            The range of the functions.
        """
        if not isinstance(dom, Set):
            raise TypeError('domain {!r} not a Set instance.'.format(dom))

        if not (isinstance(field, (RealNumbers, ComplexNumbers))):
            raise TypeError('field {!r} not a RealNumbers or '
                            'ComplexNumbers instance.'.format(field))

        super().__init__(dom, field)
        self._field = field

    @property
    def field(self):
        """Return the field of this space."""
        return self._field

    def element(self, fcall=None):
        """Create a :class:`FunctionSpace` element.

        Parameters
        ----------
        fcall : `callable`, optional
            The actual instruction for out-of-place evaluation.
            It must return an :attr:`FunctionSet.range` element or a
            `numpy.ndarray` of such (vectorized call).

            If fcall is a :class:`FunctionSet.Vector`, it is wrapped
            as a new :class:`FunctionSpace.Vector`.

        Returns
        -------
        element : :class:`FunctionSpace.Vector`
            The new element.
        """
        if fcall is None:
            return self.zero()
        else:
            return super().element(fcall)

    def _lincomb(self, a, x, b, y, out):
        """Raw linear combination of ``x`` and ``y``.

        Notes
        -----
        The additions and multiplications are implemented via a simple
        Python function, so the resulting function is probably slow.
        """
        # Store to allow aliasing
        x_old_call = x._call
        y_old_call = y._call

        def lincomb_call(*x):
            """Linear combination, call version."""
            # Due to vectorization, at least one call must be made to
            # ensure the correct final shape. The rest is optimized as
            # far as possible.
            if a == 0 and b != 0:
                out = y_old_call(*x)
                if b != 1:
                    out *= b
            elif b == 0:  # Contains the case a == 0
                out = x_old_call(*x)
                if a != 1:
                    out *= a
            else:
                out = x_old_call(*x)
                if a != 1:
                    out *= a
                tmp = y_old_call(*x)
                if b != 1:
                    tmp *= b
                out += tmp

            return out

        def lincomb_apply(out, *x):
            """Linear combination, apply version."""
            # TODO: allow also CudaRn-like container types
            if not isinstance(out, np.ndarray):
                raise TypeError('in-place evaluation only possible if output '
                                'is of type `numpy.ndarray`.')
            if a == 0 and b == 0:
                out *= 0
            elif a == 0 and b != 0:
                y_old_apply(out, *x)
                if b != 1:
                    out *= b
            elif b == 0 and a != 0:
                x_old_apply(out, *x)
                if a != 1:
                    out *= a
            else:
                tmp = np.empty_like(out)
                x_old_apply(out, *x)
                y_old_apply(tmp, *x)
                if a != 1:
                    out *= a
                if b != 1:
                    tmp *= b

                out += tmp

        out._call = lincomb_call

    def zero(self):
        """The function mapping everything to zero.

        Notes
        -----
        Since :meth:`FunctionSpace._lincomb` is slow,
        we implement this function directly.
        """
        def zero_(*_):
            """The zero function."""
            return self.field.element(0.0)
        return self.element(zero_)

    def __eq__(self, other):
        """``s.__eq__(other) <==> s == other``.

        Returns
        -------
        equals : `bool`
            `True` if ``other`` is a :class:`FunctionSpace` with
            same :attr:`FunctionSet.domain` and :attr:`FunctionSet.range`,
            `False` otherwise.
        """
        # TODO: equality also for FunctionSet instances?
        if other is self:
            return True

        return (isinstance(other, FunctionSpace) and
                self.domain == other.domain and
                self.range == other.range)

    def _multiply(x, y):
        """Raw pointwise multiplication of two functions.

        Notes
        -----
        The multiplication is implemented with a simple Python
        function, so the resulting function object is probably slow.
        """
        x_old = x.function
        y_old = y.function

        def product(arg):
            """The actual product function."""
            return x_old(arg) * y_old(arg)
        y._function = product

    def __repr__(self):
        """``s.__repr__() <==> repr(s)``."""
        return 'FunctionSpace({!r}, {!r})'.format(self.domain, self.range)

    def __str__(self):
        """``s.__str__() <==> str(s)``."""
        return 'FunctionSpace({}, {})'.format(self.domain, self.range)

    class Vector(FunctionSet.Vector, LinearSpace.Vector):
        """Representation of a :class:`FunctionSpace` element."""

        def __init__(self, fspace, fcall=None):
            """Initialize a new instance.

            Parameters
            ----------
            fspace : :class:`FunctionSpace`
                The set of functions this element lives in
            fcall : `callable`, optional
                The actual instruction for out-of-place evaluation.
                It must return an :attr:`FunctionSet.range` element or a
                `numpy.ndarray` of such (vectorized call).

            *At least one of the arguments ``fcall`` and ``fapply`` must
            be provided.*
            """
            if not isinstance(fspace, FunctionSpace):
                raise TypeError('function space {} not a `FunctionSpace` '
                                'instance.'.format(fspace))

            super().__init__(fspace, fcall)


if __name__ == '__main__':
    from doctest import testmod, NORMALIZE_WHITESPACE
    testmod(optionflags=NORMALIZE_WHITESPACE)
