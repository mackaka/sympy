import math
import sympy.mpmath as mpmath
import sympy.mpmath.lib as mlib
import sympy.mpmath.libmpc as mlibc
import decimal

rnd = mlib.round_nearest

from basic import Basic, Atom, Singleton, S, C, Memoizer, MemoizerArg
from sympify import _sympify, SympifyError, _sympifyit
from methods import NoRelMeths, RelMeths, ArithMeths
from power import integer_nthroot

# from mul import Mul   /cyclic/
# from power import Pow /cyclic/
# from function import FunctionClass    /cyclic/

# (a,b) -> gcd(a,b)
_gcdcache = {}

# TODO caching with decorator, but not to degrade performance
def igcd(a, b):
    """Computes integer greates common divisor of two numbers.

       The algorithm is based on the well known Euclid's algorithm. To
       improve speed igcd() has its own caching mechanizm implemented.
    """
    try:
        return _gcdcache[(a,b)]
    except KeyError:
        if a and b:
            if b < 0:
                b = -b

            while b:
                a, b = b, a % b
        else:
            a = abs(a or b)

        _gcdcache[(a,b)] = a
        return a

def ilcm(a, b):
    """Computes integer least common multiple of two numbers. """
    if a == 0 and b == 0:
        return 0
    else:
        return a * b / igcd(a, b)

@Memoizer((int, long), return_value_converter = lambda d: d.copy())
def factor_trial_division(n):
    """
    Factor any integer into a product of primes, 0, 1, and -1.
    Returns a dictionary {<prime: exponent>}.
    """
    if not n:
        return {0:1}
    factors = {}
    if n < 0:
        factors[-1] = 1
        n = -n
    if n==1:
        factors[1] = 1
        return factors
    d = 2
    while n % d == 0:
        try:
            factors[d] += 1
        except KeyError:
            factors[d] = 1
        n //= d
    d = 3
    while n > 1 and d*d <= n:
        if n % d:
            d += 2
        else:
            try:
                factors[d] += 1
            except KeyError:
                factors[d] = 1
            n //= d
    if n>1:
        try:
            factors[n] += 1
        except KeyError:
            factors[n] = 1
    return factors


class Number(Atom, RelMeths, ArithMeths):
    """
    Represents any kind of number in sympy.

    Floating point numbers are represented by the Real class.
    Integer numbers (of any size), together with rational numbers (again, there
    is no limit on their size) are represented by the Rational class.

    If you want to represent for example 1+sqrt(2), then you need to do:

    Rational(1) + sqrt(Rational(2))
    """
    is_commutative = True
    is_comparable = True
    is_bounded = True
    is_finite = True

    __slots__ = []

    # Used to make max(x._prec, y._prec) return x._prec when only x is a float
    _prec = -1

    is_Number = True

    def __new__(cls, *obj):
        if len(obj)==1: obj=obj[0]
        if isinstance(obj, (int, long)):
            return Integer(obj)
        if isinstance(obj,tuple) and len(obj)==2:
            return Rational(*obj)
        if isinstance(obj, (str,float,mpmath.mpf,decimal.Decimal)):
            return Real(obj)
        if isinstance(obj, Number):
            return obj
        raise TypeError("expected str|int|long|float|Decimal|Number object but got %r" % (obj))

    def _as_mpf_val(self, prec):
        """Evaluate to mpf tuple accurate to at least prec bits"""
        raise NotImplementedError('%s needs ._as_mpf_val() method' % \
            (self.__class__.__name__))

    def _eval_evalf(self, prec):
        return Real._new(self._as_mpf_val(prec), prec)

    def _as_mpf_op(self, prec):
        prec = max(prec, self._prec)
        return self._as_mpf_val(prec), prec

    def __float__(self):
        return mlib.to_float(self._as_mpf_val(53))

    def _eval_derivative(self, s):
        return S.Zero

    def _eval_conjugate(self):
        return self

    def _eval_order(self, *symbols):
        # Order(5, x, y) -> Order(1,x,y)
        return C.Order(S.One, *symbols)

    def __eq__(self, other):
        raise NotImplementedError('%s needs .__eq__() method' % (self.__class__.__name__))
    def __ne__(self, other):
        raise NotImplementedError('%s needs .__ne__() method' % (self.__class__.__name__))
    def __lt__(self, other):
        raise NotImplementedError('%s needs .__lt__() method' % (self.__class__.__name__))
    def __le__(self, other):
        raise NotImplementedError('%s needs .__le__() method' % (self.__class__.__name__))

    def __gt__(self, other):
        return _sympify(other).__lt__(self)
    def __ge__(self, other):
        return _sympify(other).__le__(self)

    def as_coeff_terms(self, x=None):
        # a -> c * t
        return self, tuple()


class Real(Number):
    """
    Represents a floating point number. It is capable of representing
    arbitrary-precision floating-point numbers

    Usage:
    ======
        Real(3.5)   .... 3.5 (the 3.5 was converted from a python float)
        Real("3.0000000000000005")

    Notes:
    ======
        - Real(x) with x being a Python int/long will return Integer(x)
    """
    is_real = True
    is_irrational = False
    is_integer = False

    __slots__ = ['_mpf_', '_prec']

    # mpz can't be pickled
    def __getstate__(self):
        d = Basic.__getstate__(self).copy()
        del d["_mpf_"]
        return mlib.to_pickable(self._mpf_), d

    def __setstate__(self, state):
        _mpf_, d = state
        _mpf_ = mlib.from_pickable(_mpf_)
        self._mpf_ = _mpf_
        Basic.__setstate__(self, d)

    is_Real = True

    def floor(self):
        return C.Integer(int(mlib.to_int(mlib.ffloor(self._mpf_, self._prec))))

    def ceiling(self):
        return C.Integer(int(mlib.to_int(mlib.fceil(self._mpf_, self._prec))))

    @property
    def num(self):
        return mpmath.mpf(self._mpf_)

    def _as_mpf_val(self, prec):
        return self._mpf_

    def _as_mpf_op(self, prec):
        return self._mpf_, max(prec, self._prec)

    def __new__(cls, num, prec=15):
        prec = mlib.dps_to_prec(prec)
        if isinstance(num, (int, long)):
            return Integer(num)
        if isinstance(num, (str, decimal.Decimal)):
            _mpf_ = mlib.from_str(str(num), prec)
        elif isinstance(num, tuple) and len(num) == 4:
            _mpf_ = num
        else:
            _mpf_ = mpmath.mpf(num)._mpf_
        if not num:
            return C.Zero()
        obj = Basic.__new__(cls)
        obj._mpf_ = _mpf_
        obj._prec = prec
        return obj

    @classmethod
    def _new(cls, _mpf_, _prec):
        if _mpf_ == mlib.fzero:
            return S.Zero
        obj = Basic.__new__(cls)
        obj._mpf_ = _mpf_
        obj._prec = _prec
        return obj

    def _hashable_content(self):
        return (self._mpf_, self._prec)

    def tostr(self, level=0):
        r = mlib.to_str(self._mpf_, mlib.prec_to_dps(self._prec))
        if self.precedence<=level:
            return '(%s)' % (r)
        return r

    def torepr(self):
        dps = mlib.prec_to_dps(self._prec)
        r = mlib.to_str(self._mpf_, dps+3)
        return '%s(%r, prec=%i)' % (self.__class__.__name__, r, dps)

    def _eval_is_positive(self):
        return self.num > 0

    def _eval_is_negative(self):
        return self.num < 0

    def __neg__(self):
        return Real._new(mlib.fneg(self._mpf_), self._prec)

    def __mul__(self, other):
        try:
            other = _sympify(other)
        except SympifyError:
            return NotImplemented
        if isinstance(other, Number):
            rhs, prec = other._as_mpf_op(self._prec)
            return Real._new(mlib.fmul(self._mpf_, rhs, prec, rnd), prec)
        return Number.__mul__(self, other)

    def __add__(self, other):
        try:
            other = _sympify(other)
        except SympifyError:
            return NotImplemented
        if (other is S.NaN) or (self is NaN):
            return S.NaN
        if isinstance(other, Number):
            rhs, prec = other._as_mpf_op(self._prec)
            return Real._new(mlib.fadd(self._mpf_, rhs, prec, rnd), prec)
        return Number.__add__(self, other)

    def _eval_power(b, e):
        """
        b is Real but not equal to rationals, integers, 0.5, oo, -oo, nan
        e is symbolic object but not equal to 0, 1

        (-p) ** r -> exp(r * log(-p)) -> exp(r * (log(p) + I*Pi)) ->
                  -> p ** r * (sin(Pi*r) + cos(Pi*r) * I)
        """
        if isinstance(e, Number):
            if isinstance(e, Integer):
                prec = b._prec
                return Real._new(mlib.fpowi(b._mpf_, e.p, prec, rnd), prec)
            e, prec = e._as_mpf_op(b._prec)
            b = b._mpf_
            try:
                y = mlib.fpow(b, e, prec, rnd)
                return Real._new(y, prec)
            except mlib.ComplexResult:
                re, im = mlibc.mpc_pow((b, mlib.fzero), (e, mlib.fzero), prec, rnd)
                return Real._new(re, prec) + Real._new(im, prec) * S.ImaginaryUnit

    def __abs__(self):
        return Real._new(mlib.fabs(self._mpf_), self._prec)

    def __int__(self):
        return int(mlib.to_int(self._mpf_))

    def __eq__(self, other):
        try:
            other = _sympify(other)
        except SympifyError:
            return False    # sympy != other  -->  not ==
        if isinstance(other, NumberSymbol):
            if other.is_irrational: return False
            return other.__eq__(self)
        if other.is_comparable: other = other.evalf()
        if isinstance(other, Number):
            return bool(mlib.feq(self._mpf_, other._as_mpf_val(self._prec)))
        return False    # Real != non-Number

    def __ne__(self, other):
        try:
            other = _sympify(other)
        except SympifyError:
            return True     # sympy != other
        if isinstance(other, NumberSymbol):
            if other.is_irrational: return True
            return other.__ne__(self)
        if other.is_comparable: other = other.evalf()
        if isinstance(other, Number):
            return bool(not mlib.feq(self._mpf_, other._as_mpf_val(self._prec)))
        return True     # Real != non-Number

    def __lt__(self, other):
        try:
            other = _sympify(other)
        except SympifyError:
            return False    # sympy > other
        if isinstance(other, NumberSymbol):
            return other.__ge__(self)
        if other.is_comparable: other = other.evalf()
        if isinstance(other, Number):
            return bool(mlib.flt(self._mpf_, other._as_mpf_val(self._prec)))
        return RelMeths.__lt__(self, other)

    def __le__(self, other):
        try:
            other = _sympify(other)
        except SympifyError:
            return False    # sympy > other  -->  ! <=
        if isinstance(other, NumberSymbol):
            return other.__gt__(self)
        if other.is_comparable: other = other.evalf()
        if isinstance(other, Number):
            return bool(mlib.fle(self._mpf_, other._as_mpf_val(self._prec)))
        return RelMeths.__le__(self, other)

    def epsilon_eq(self, other, epsilon="10e-16"):
        return abs(self - other) < Real(epsilon)

def _parse_rational(s):
    """Parse rational number from string representation"""
    # Simple fraction
    if "/" in s:
        p, q = s.split("/")
        return int(p), int(q)
    # Recurring decimal
    elif "[" in s:
        sign = 1
        if s[0] == "-":
            sign = -1
            s = s[1:]
        s, periodic = s.split("[")
        periodic = periodic.rstrip("]")
        offset = len(s) - s.index(".") - 1
        n1 = int(periodic)
        n2 = int("9" * len(periodic))
        r = Rational(*_parse_rational(s)) + Rational(n1, n2*10**offset)
        return sign*r.p, r.q
    # Ordinary decimal string. Use the Decimal class's built-in parser
    else:
        sign, digits, expt = decimal.Decimal(s).as_tuple()
        p = (1, -1)[sign] * int("".join(str(x) for x in digits))
        if expt >= 0:
            return p*(10**expt), 1
        else:
            return p, 10**-expt


class Rational(Number):
    """Represents integers and rational numbers (p/q) of any size.

    Examples
    ========
        >>> Rational(3)
        3
        >>> Rational(1,2)
        1/2

    You can create a rational from a string:
        >>> Rational("3/5")
        3/5
        >>> Rational("1.23")
        123/100

    Use square brackets to indicate a recurring decimal:
        >>> Rational("0.[333]")
        1/3
        >>> Rational("1.2[05]")
        1193/990
        >>> float(Rational(1193,990))
        1.2050505050505051


    Low-level
    ---------

    Access nominator and denominator as .p and .q:
        >>> r = Rational(3,4)
        >>> r
        3/4
        >>> r.p
        3
        >>> r.q
        4
    """
    is_real = True
    is_integer = False
    is_rational = True

    __slots__ = ['p', 'q']

    is_Rational = True

    @Memoizer(type, (int, long, str), MemoizerArg((int, long, type(None)), name="q"))
    def __new__(cls, p, q = None):
        if q is None:
            if isinstance(p, str):
                p, q = _parse_rational(p)
            else:
                return Integer(p)
        if q==0:
            if p==0: return S.NaN
            if p<0: return S.NegativeInfinity
            return S.Infinity
        if q<0:
            q = -q
            p = -p
        n = igcd(abs(p), q)
        if n>1:
            p /= n
            q /= n
        if q==1: return Integer(p)
        if p==1 and q==2: return S.Half
        obj = Basic.__new__(cls)
        obj.p = p
        obj.q = q
        #obj._args = (p, q)
        return obj

    def _hashable_content(self):
        return (self.p, self.q)

    def tostr(self, level=0):
        if self.precedence<=level:
            return '(%s/%s)' % (self.p, self.q)
        return '%s/%s' % (self.p, self.q)

    def torepr(self):
        return '%s(%r, %r)' % (self.__class__.__name__, self.p, self.q)

    @property
    def precedence(self):
        if self.p < 0:
            return Basic.Add_precedence
        return Basic.Mul_precedence

    def _eval_is_positive(self):
        return self.p > 0

    def _eval_is_zero(self):
        return self.p == 0

    def __neg__(self): return Rational(-self.p, self.q)

    @_sympifyit('other', NotImplemented)
    def __mul__(self, other):
        if (other is S.NaN) or (self is S.NaN):
            return S.NaN
        if isinstance(other, Real):
            return other * self
        if isinstance(other, Rational):
            return Rational(self.p * other.p, self.q * other.q)
        return Number.__mul__(self, other)

    # TODO reorder
    @_sympifyit('other', NotImplemented)
    def __add__(self, other):
        if (other is S.NaN) or (self is S.NaN):
            return S.NaN
        if isinstance(other, Real):
            return other + self
        if isinstance(other, Rational):
            if self.is_unbounded:
                if other.is_bounded:
                    return self
                elif self==other:
                    return self
            else:
                if other.is_unbounded:
                    return other
            return Rational(self.p * other.q + self.q * other.p, self.q * other.q)
        return Number.__add__(self, other)

    def _eval_power(b, e):
        if isinstance(e, Number):
            if (e is S.NaN): return S.NaN
            if isinstance(e, Real):
                return b._eval_evalf(e._prec) ** e
            if e.is_negative:
                # (3/4)**-2 -> (4/3)**2
                ne = -e
                if (ne is S.One):
                    return Rational(b.q, b.p)
                return Rational(b.q, b.p) ** ne
            if (e is S.Infinity):
                if b.p > b.q:
                    # (3/2)**oo -> oo
                    return S.Infinity
                if b.p < -b.q:
                    # (-3/2)**oo -> oo + I*oo
                    return S.Infinity + S.Infinity * S.ImaginaryUnit
                return S.Zero
            if isinstance(e, Integer):
                # (4/3)**2 -> 4**2 / 3**2
                return Rational(b.p ** e.p, b.q ** e.p)
            if isinstance(e, Rational):
                if b.p != 1:
                    # (4/3)**(5/6) -> 4**(5/6) * 3**(-5/6)
                    return Integer(b.p) ** e * Integer(b.q) ** (-e)
                if b >= 0:
                    return Integer(b.q)**Rational(e.p * (e.q-1), e.q) / ( Integer(b.q) ** Integer(e.p))
                else:
                    return (-1)**e * (-b)**e

        c,t = b.as_coeff_terms()
        if e.is_even and isinstance(c, Number) and c < 0:
            return (-c * Mul(*t)) ** e

        return

    def _as_mpf_val(self, prec):
        return mlib.from_rational(self.p, self.q, prec, rnd)

    def __abs__(self):
        return Rational(abs(self.p), self.q)

    def __int__(self):
        return int(self.p//self.q)

    def __eq__(self, other):
        try:
            other = _sympify(other)
        except SympifyError:
            return False    # sympy != other  -->  not ==
        if isinstance(other, NumberSymbol):
            if other.is_irrational: return False
            return other.__eq__(self)
        if isinstance(self, Number) and isinstance(other, FunctionClass):
            return False
        if other.is_comparable and not isinstance(other, Rational): other = other.evalf()
        if isinstance(other, Number):
            if isinstance(other, Real):
                return bool(mlib.feq(self._as_mpf_val(other._prec), other._mpf_))
            return bool(self.p==other.p and self.q==other.q)

        return False    # Rational != non-Number

    def __ne__(self, other):
        try:
            other = _sympify(other)
        except SympifyError:
            return True     # sympy != other
        if isinstance(other, NumberSymbol):
            if other.is_irrational: return True
            return other.__ne__(self)
        if other.is_comparable and not isinstance(other, Rational): other = other.evalf()
        if isinstance(other, Number):
            if isinstance(other, Real):
                return bool(not mlib.feq(self._as_mpf_val(other._prec), other._mpf_))
            return bool(self.p!=other.p or self.q!=other.q)

        return True     # Rational != non-Number

    def __lt__(self, other):
        try:
            other = _sympify(other)
        except SympifyError:
            return False    # sympy > other  --> not <
        if isinstance(other, NumberSymbol):
            return other.__ge__(self)
        if other.is_comparable and not isinstance(other, Rational): other = other.evalf()
        if isinstance(other, Number):
            if isinstance(other, Real):
                return bool(mlib.flt(self._as_mpf_val(other._prec), other._mpf_))
            return bool(self.p * other.q < self.q * other.p)
        return RelMeths.__lt__(self, other)

    def __le__(self, other):
        try:
            other = _sympify(other)
        except SympifyError:
            return False    # sympy > other  -->  not <=
        if isinstance(other, NumberSymbol):
            return other.__gt__(self)
        if other.is_comparable and not isinstance(other, Rational): other = other.evalf()
        if isinstance(other, Number):
            if isinstance(other, Real):
                return bool(mlib.fle(self._as_mpf_val(other._prec), other._mpf_))
            return bool(self.p * other.q <= self.q * other.p)
        return RelMeths.__le__(self, other)

    def factors(self):
        f = factor_trial_division(self.p).copy()
        for p,e in factor_trial_division(self.q).items():
            try: f[p] += -e
            except KeyError: f[p] = -e
        fi = {}
        for p,e in f.items():
            if e==0:
                del f[p]
            else:
                try: fi[e] *= p
                except KeyError: fi[e] = p
        f = {}
        for e,p in fi.items():
            f[p] = e
        if len(f)>1 and f.has_key(1): del f[1]
        return f

    def as_numer_denom(self):
        return Integer(self.p), Integer(self.q)

    def _sage_(self):
        import sage.all as sage
        #XXX: fixme, this should work:
        #return sage.Integer(self[0])/sage.Integer(self[1])
        return sage.Integer(self.p)/sage.Integer(self.q)

# int -> Integer
_intcache = {}

class Integer(Rational):

    q = 1
    is_integer = True

    is_Integer = True

    __slots__ = ['p']

    def _as_mpf_val(self, prec):
        return mlib.from_int(self.p)

    # TODO caching with decorator, but not to degrade performance
    def __new__(cls, i):
        try:
            return _intcache[i]
        except KeyError:
            if not isinstance(i, (int, long)):
                raise ValueError('invalid argument for Integer: %r' % (i,))
            obj = Basic.__new__(cls)
            obj.p = i
            _intcache[i] = obj
            return obj

    # Arithmetic operations are here for efficiency
    def __neg__(self):
        return Integer(-self.p)

    def __abs__(self):
        if self.p >= 0:
            return self
        else:
            return Integer(-self.p)

    # TODO make it decorator + bytecodehacks?
    def __add__(a, b):
        if type(b) is int:
            return Integer(a.p + b)
        elif isinstance(b, Integer):
            return Integer(a.p + b.p)
        return Rational.__add__(a, b)   # a,b -not- b,a

    def __radd__(a, b):
        if type(b) is int:
            return Integer(b + a.p)
        elif isinstance(b, Integer):
            return Integer(b.p + a.p)
        return Rational.__add__(a, b)

    def __mul__(a, b):
        if type(b) is int:
            return Integer(a.p * b)
        elif isinstance(b, Integer):
            return Integer(a.p * b.p)
        return Rational.__mul__(a, b)

    def __rmul__(a, b):
        if type(b) is int:
            return Integer(b * a.p)
        elif isinstance(b, Integer):
            return Integer(b.p * a.p)
        return Rational.__mul__(a, b)

    # XXX __pow__ ?

    # XXX do we need to define __cmp__ ?
#   def __cmp__(a, b):

    def __eq__(a, b):
        if type(b) is int:
            return (a.p == b)
        elif isinstance(b, Integer):
            return (a.p == b.p)
        return Rational.__eq__(a, b)

    def __ne__(a, b):
        if type(b) is int:
            return (a.p != b)
        elif isinstance(b, Integer):
            return (a.p != b.p)
        return Rational.__ne__(a, b)

    def __gt__(a, b):
        if type(b) is int:
            return (a.p >  b)
        elif isinstance(b, Integer):
            return (a.p >  b.p)
        return Rational.__gt__(a, b)

    def __lt__(a, b):
        if type(b) is int:
            return (a.p <  b)
        elif isinstance(b, Integer):
            return (a.p <  b.p)
        return Rational.__lt__(a, b)

    def __ge__(a, b):
        if type(b) is int:
            return (a.p >= b)
        elif isinstance(b, Integer):
            return (a.p >= b.p)
        return Rational.__ge__(a, b)

    def __le__(a, b):
        if type(b) is int:
            return (a.p <= b)
        elif isinstance(b, Integer):
            return (a.p <= b.p)
        return Rational.__le__(a, b)

    ########################################

    def _eval_is_odd(self):
        return bool(self.p % 2)

    @property
    def precedence(self):
        if self.p < 0:
            return 40 # same as Add
        return Atom.precedence

    def tostr(self, level=0):
        if self.precedence<=level:
            return '(%s)' % (self.p)
        return str(self.p)

    def torepr(self):
        return '%s(%r)' % (self.__class__.__name__, self.p)

    def _eval_power(b, e):
        if isinstance(e, Number):
            if e is S.NaN: return S.NaN
            if isinstance(e, Real):
                return b._eval_evalf(e._prec) ** e
            if e.is_negative:
                # (3/4)**-2 -> (4/3)**2
                ne = -e
                if ne is S.One:
                    return Rational(1, b.p)
                return Rational(1, b.p) ** ne
            if e is S.Infinity:
                if b.p > 1:
                    # (3)**oo -> oo
                    return S.Infinity
                if b.p < -1:
                    # (-3)**oo -> oo + I*oo
                    return S.Infinity + S.Infinity * S.ImaginaryUnit
                return S.Zero
            if isinstance(e, Integer):
                # (4/3)**2 -> 4**2 / 3**2
                return Integer(b.p ** e.p)
            if isinstance(e, Rational):
                if b == -1:  # any one has tested this ???
                    # calculate the roots of -1
                    if e.q.is_odd:
                        return -1
                    r = cos(pi/e.q) + S.ImaginaryUnit*sin(pi/e.q)
                    return r**e.p
                if b >= 0:
                    x, xexact = integer_nthroot(b.p, e.q)
                    if xexact:
                        res = Integer(x ** abs(e.p))
                        if e >= 0:
                            return res
                        else:
                            return 1/res
                    else:
                        if b > 2**32: #Prevent from factorizing too big integers:
                            for i in xrange(2, e.q/2 + 1): #OLD CODE
                                if e.q % i == 0:
                                    x, xexact = integer_nthroot(b.p, i)
                                    if xexact:
                                        return Integer(x)**(e * i)
                            # Try to get some part of the base out, if exponent > 1
                            if e.p > e.q:
                                i = e.p / e.q
                                r = e.p % e.q
                                return b**i * b**Rational(r, e.q)
                            return


                        dict = b.factors()

                        out_int = 1
                        sqr_int = 1
                        sqr_gcd = 0

                        sqr_dict = {}

                        for prime,exponent in dict.iteritems():
                            exponent *= e.p
                            div_e = exponent / e.q
                            div_m = exponent % e.q

                            if div_e > 0:
                                out_int *= prime**div_e
                            if div_m > 0:
                                sqr_dict[prime] = div_m

                        for p,ex in sqr_dict.iteritems():
                            if sqr_gcd == 0:
                                sqr_gcd = ex
                            else:
                                sqr_gcd = igcd(sqr_gcd, ex)

                        for k,v in sqr_dict.iteritems():
                            sqr_int *= k**(v/sqr_gcd)

                        if sqr_int == b.p and out_int == 1:
                            return None

                        return out_int * Pow(sqr_int , Rational(sqr_gcd, e.q))
                else:
                    if e.q == 2:
                        return S.ImaginaryUnit ** e.p * (-b)**e
                    else:
                        return None

        c,t = b.as_coeff_terms()
        if e.is_even and isinstance(c, Number) and c < 0:
            return (-c * Mul(*t)) ** e

        return

    def _eval_is_prime(self):
        if self.p < 0:
            return False

    def as_numer_denom(self):
        return self, S.One

    def __floordiv__(self, other):
        return Integer(self.p // Integer(other).p)

    def __rfloordiv__(self, other):
        return Integer(Integer(other).p // self.p)

class Zero(Singleton, Integer):

    p = 0
    q = 1
    is_positive = False
    is_negative = False
    is_finite = False
    is_zero = True
    is_prime = False
    is_composite = True

    __slots__ = []

    @staticmethod
    def __abs__():
        return S.Zero

    @staticmethod
    def __neg__():
        return S.Zero

    def _eval_power(b, e):
        if e.is_negative:
            return S.Infinity
        if e.is_positive:
            return b
        d = e.evalf()
        if isinstance(d, Number):
            if d.is_negative:
                return S.Infinity
            return b
        coeff, terms = e.as_coeff_terms()
        if coeff.is_negative:
            return S.Infinity ** Mul(*terms)
        if coeff is not S.One:
            return b ** Mul(*terms)

    def _eval_order(self, *symbols):
        # Order(0,x) -> 0
        return self

class One(Singleton, Integer):

    p = 1
    q = 1

    is_prime = True

    __slots__ = []

    def _eval_evalf(self, prec):
        return self

    @staticmethod
    def __abs__():
        return S.One

    @staticmethod
    def __neg__():
        return S.NegativeOne

    def _eval_power(b, e):
        return b

    def _eval_order(self, *symbols):
        return

class NegativeOne(Singleton, Integer):

    p = -1
    q = 1

    __slots__ = []

    def _eval_evalf(self, prec):
        return self

    @staticmethod
    def __abs__():
        return S.One

    @staticmethod
    def __neg__():
        return S.One

    def _eval_power(b, e):
        if e.is_odd: return S.NegativeOne
        if e.is_even: return S.One
        if isinstance(e, Number):
            if isinstance(e, Real):
                return Real(-1.0) ** e
            if e is S.NaN:
                return S.NaN
            if e is S.Infinity  or  e is S.NegativeInfinity:
                return S.NaN
            if e is S.Half:
                return S.ImaginaryUnit
            if isinstance(e, Rational):
                if e.q == 2:
                    return S.ImaginaryUnit ** Integer(e.p)
                q = int(e)
                if q:
                    q = Integer(q)
                    return b ** q * b ** (e - q)
        return

class Half(Singleton, Rational):

    p = 1
    q = 2

    __slots__ = []

    @staticmethod
    def __abs__():
        return S.Half


class Infinity(Singleton, Rational):

    p = 1
    q = 0

    __slots__ = []

    is_commutative = True
    is_positive = True
    is_bounded = False
    is_finite = None
    is_odd = None

    @staticmethod
    def __abs__():
        return S.Infinity

    @staticmethod
    def __neg__():
        return S.NegativeInfinity

    def tostr(self, level=0):
        return 'oo'

    def _eval_power(b, e):
        """
        e is symbolic object but not equal to 0, 1

        oo ** nan -> nan
        oo ** (-p) -> 0, p is number, oo
        """
        if e.is_positive:
            return S.Infinity
        if e.is_negative:
            return S.Zero
        if isinstance(e, Number):
            if e is S.NaN:
                return S.NaN
        d = e.evalf()
        if isinstance(d, Number):
            return b ** d
        return

    def _as_mpf_val(self, prec):
        return mlib.finf

class NegativeInfinity(Singleton, Rational):

    p = -1
    q = 0

    __slots__ = []

    is_commutative = True
    is_real = True
    is_positive = False
    is_bounded = False
    is_finite = False

    precedence = 40 # same as Add

    @staticmethod
    def __abs__():
        return S.Infinity

    @staticmethod
    def __neg__():
        return S.Infinity

    def tostr(self, level=0):
        return '-oo'

    def _eval_power(b, e):
        """
        e is symbolic object but not equal to 0, 1

        (-oo) ** nan -> nan
        (-oo) ** oo  -> nan
        (-oo) ** (-oo) -> nan
        (-oo) ** e -> oo, e is positive even integer
        (-oo) ** o -> -oo, o is positive odd integer

        """
        if isinstance(e, Number):
            if (e is S.NaN)  or  (e is S.Infinity)  or  (e is S.NegativeInfinity):
                return S.NaN
            if isinstance(e, Integer):
                if e.is_positive:
                    if e.is_odd:
                        return S.NegativeInfinity
                    return S.Infinity
            return S.NegativeOne**e * S.Infinity ** e
        return

    def _as_mpf_val(self, prec):
        return mlib.fninf

class NaN(Singleton, Rational):

    p = 0
    q = 0

    is_commutative = True
    is_real = None
    is_comparable = None
    is_bounded = None
    #is_unbounded = False

    __slots__ = []

    def tostr(self, level=0):
        return 'nan'

    def _as_mpf_val(self, prec):
        return mlib.fnan

    def _eval_power(b, e):
        if e is S.Zero:
            return S.One
        return b

class ComplexInfinity(Singleton, Atom, NoRelMeths, ArithMeths):

    is_commutative = True
    is_comparable = None
    is_bounded = False
    is_real = None

    __slots__ = []

    @staticmethod
    def __abs__():
        return S.Infinity

    @staticmethod
    def __neg__():
        return S.ComplexInfinity

    def tostr(self, level=0):
        return 'zoo'

    def _eval_power(b, e):
        if e is S.ComplexInfinity:
            return S.NaN

        if isinstance(e, Number):
            if e is S.Zero:
                return S.NaN
            else:
                if e.is_positive:
                    return S.ComplexInfinity
                else:
                    return S.Zero

class NumberSymbol(Singleton, Atom, RelMeths, ArithMeths):

    is_commutative = True
    is_comparable = True
    is_bounded = True
    is_finite = True

    __slots__ = []

    is_NumberSymbol = True

    def approximation(self, number_cls):
        """ Return an interval with number_cls endpoints
        that contains the value of NumberSymbol.
        If not implemented, then return None.
        """

    def _eval_evalf(self, prec):
        return Real._new(self._as_mpf_val(prec), prec)

    def _eval_derivative(self, s):
        return S.Zero

    def __eq__(self, other):
        try:
            other = _sympify(other)
        except SympifyError:
            return False    # sympy != other  -->  not ==
        if self is other: return True
        if isinstance(other, Number) and self.is_irrational: return False

        return False    # NumberSymbol != non-(Number|self)

    def __ne__(self, other):
        try:
            other = _sympify(other)
        except SympifyError:
            return True     # sympy != other
        if self is other: return False
        if isinstance(other, Number) and self.is_irrational: return True

        return True     # NumberSymbol != non(Number|self)

    def __lt__(self, other):
        try:
            other = _sympify(other)
        except SympifyError:
            return False    # sympy > other  --> not <
        if self is other: return False
        if isinstance(other, Number):
            approx = self.approximation_interval(other.__class__)
            if approx is not None:
                l,u = approx
                if other < l: return False
                if other > u: return True
            return self.evalf()<other
        if other.is_comparable:
            other = other.evalf()
            return self.evalf()<other
        return RelMeths.__lt__(self, other)
    def __le__(self, other):
        try:
            other = _sympify(other)
        except SympifyError:
            return False    # sympy > other  --> not <=
        if self is other: return True
        if other.is_comparable: other = other.evalf()
        if isinstance(other, Number):
            return self.evalf()<=other
        return RelMeths.__le__(self, other)
    def __gt__(self, other):
        return (-self) < (-other)
    def __ge__(self, other):
        return (-self) <= (-other)


class Exp1(NumberSymbol):

    is_real = True
    is_positive = True
    is_negative = False # XXX Forces is_negative/is_nonnegative
    is_irrational = True

    __slots__ = []

    @staticmethod
    def __abs__():
        return S.Exp1

    def tostr(self, level=0):
        return 'E'

    def _as_mpf_val(self, prec):
        return mlib.fe(prec)

    def approximation_interval(self, number_cls):
        if issubclass(number_cls,Integer):
            return (Integer(2),Integer(3))
        elif issubclass(number_cls,Rational):
            pass

    def _eval_power(self, exp):
        return C.exp(exp)

class Pi(NumberSymbol):

    is_real = True
    is_positive = True
    is_negative = False
    is_irrational = True

    __slots__ = []

    @staticmethod
    def __abs__():
        return S.Pi

    def _as_mpf_val(self, prec):
        return mlib.fpi(prec)

    def approximation_interval(self, number_cls):
        if issubclass(number_cls, Integer):
            return (Integer(3), Integer(4))
        elif issubclass(number_cls, Rational):
            return (Rational(223,71), Rational(22,7))

    def tostr(self, level=0):
        return 'pi'

class GoldenRatio(NumberSymbol):

    is_real = True
    is_positive = True
    is_negative = False
    is_irrational = True

    __slots__ = []

    def _as_mpf_val(self, prec):
        return mlib.from_man_exp(mpmath.specfun.phi_fixed(prec+10), -prec-10)

    def _eval_expand_func(self, *args):
        return S.Half + S.Half*S.Sqrt(5)

    def approximation_interval(self, number_cls):
        if issubclass(number_cls, Integer):
            return (S.One, Rational(2))
        elif issubclass(number_cls, Rational):
            pass

    def tostr(self, level=0):
        return 'GoldenRatio'

class EulerGamma(NumberSymbol):

    is_real = True
    is_positive = True
    is_negative = False
    is_irrational = None

    __slots__ = []

    def _as_mpf_val(self, prec):
        return mlib.from_man_exp(mpmath.specfun.euler_fixed(prec+10), -prec-10)

    def approximation_interval(self, number_cls):
        if issubclass(number_cls, Integer):
            return (S.Zero, S.One)
        elif issubclass(number_cls, Rational):
            return (S.Half, Rational(3, 5))

    def tostr(self, level=0):
        return 'EulerGamma'

class Catalan(NumberSymbol):

    is_real = True
    is_positive = True
    is_negative = False
    is_irrational = None

    __slots__ = []

    def _as_mpf_val(self, prec):
        return mlib.from_man_exp(mpmath.specfun.catalan_fixed(prec+10), -prec-10)

    def approximation_interval(self, number_cls):
        if issubclass(number_cls, Integer):
            return (S.Zero, S.One)
        elif issubclass(number_cls, Rational):
            return (Rational(9, 10), S.One)

    def tostr(self, level=0):
        return 'Catalan'

class ImaginaryUnit(Singleton, Atom, RelMeths, ArithMeths):

    is_commutative = True
    is_imaginary = True
    is_bounded = True
    is_finite = True

    __slots__ = []

    @staticmethod
    def __abs__():
        return S.One

    def _eval_evalf(self, prec):
        return self

    def tostr(self, level=0):
        return 'I'

    def _eval_conjugate(self):
        return -S.ImaginaryUnit

    def _eval_derivative(self, s):
        return S.Zero

    def _eval_power(b, e):
        """
        b is I = sqrt(-1)
        e is symbolic object but not equal to 0, 1

        I ** r -> (-1)**(r/2) -> exp(r/2 * Pi * I) -> sin(Pi*r/2) + cos(Pi*r/2) * I, r is decimal
        I ** 0 mod 4 -> 1
        I ** 1 mod 4 -> I
        I ** 2 mod 4 -> -1
        I ** 3 mod 4 -> -I
        """


        if isinstance(e, Number):
            #if isinstance(e, Decimal):
            #    a = decimal_math.pi() * exponent.num / 2
            #    return Decimal(decimal_math.sin(a) + decimal_math.cos(a) * ImaginaryUnit())
            if isinstance(e, Integer):
                e = e.p % 4
                if e==0: return S.One
                if e==1: return S.ImaginaryUnit
                if e==2: return -S.One
                return -S.ImaginaryUnit
            return (-S.One) ** (e * S.Half)
        return

    def as_base_exp(self):
        return -S.One, S.Half

# /cyclic/
import basic as _
_.Number    = Number
_.Integer   = Integer
_.Rational  = Rational
_.Real      = Real
del _

import add as _
_.Number    = Number
del _

import mul as _
_.Number    = Number
_.Integer   = Integer
_.Real      = Real
del _

import power as _
_.Number    = Number
_.Rational  = Rational
_.Integer   = Integer
del _

import sympify as _
_.Integer   = Integer
_.Real      = Real
del _

# ----

_intcache[0] = S.Zero
_intcache[1] = S.One
_intcache[-1]= S.NegativeOne

Basic.singleton['E'] = Exp1
Basic.singleton['pi'] = Pi
Basic.singleton['I'] = ImaginaryUnit
Basic.singleton['oo'] = Infinity
Basic.singleton['nan'] = NaN

Basic.singleton['zoo'] = ComplexInfinity

Basic.singleton['GoldenRatio'] = GoldenRatio
Basic.singleton['EulerGamma'] = EulerGamma
Basic.singleton['Catalan'] = Catalan
