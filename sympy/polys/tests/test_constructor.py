"""Tests for tools for constructing domains for expressions. """

from sympy.polys.constructor import construct_domain
from sympy.polys.domains import ZZ, QQ, RR, EX

from sympy import S, sqrt, sin
from sympy.abc import x, y

def test_construct_domain():
    assert construct_domain([1, 2, 3]) == (ZZ, [ZZ(1), ZZ(2), ZZ(3)])
    assert construct_domain([1, 2, 3], field=True) == (QQ, [QQ(1), QQ(2), QQ(3)])

    assert construct_domain([S(1), S(2), S(3)]) == (ZZ, [ZZ(1), ZZ(2), ZZ(3)])
    assert construct_domain([S(1), S(2), S(3)], field=True) == (QQ, [QQ(1), QQ(2), QQ(3)])

    assert construct_domain([S(1)/2, S(2)]) == (QQ, [QQ(1,2), QQ(2)])
    assert construct_domain([3.14, 1, S(1)/2]) == (RR, [RR(3.14), RR(1.0), RR(0.5)])

    assert construct_domain([3.14, sqrt(2)], extension=None) == (EX, [EX(3.14), EX(sqrt(2))])
    assert construct_domain([3.14, sqrt(2)], extension=True) == (EX, [EX(3.14), EX(sqrt(2))])

    assert construct_domain([1, sqrt(2)], extension=None) == (EX, [EX(1), EX(sqrt(2))])

    alg = QQ.algebraic_field(sqrt(2))

    assert construct_domain([7, S(1)/2, sqrt(2)], extension=True) == \
        (alg, [alg.convert(7), alg.convert(S(1)/2), alg.convert(sqrt(2))])

    alg = QQ.algebraic_field(sqrt(2)+sqrt(3))

    assert construct_domain([7, sqrt(2), sqrt(3)], extension=True) == \
        (alg, [alg.convert(7), alg.convert(sqrt(2)), alg.convert(sqrt(3))])

    dom = ZZ[x]

    assert construct_domain([2*x, 3]) == \
        (dom, [dom.convert(2*x), dom.convert(3)])

    dom = ZZ[x,y]

    assert construct_domain([2*x, 3*y]) == \
        (dom, [dom.convert(2*x), dom.convert(3*y)])

    dom = QQ[x]

    assert construct_domain([x/2, 3]) == \
        (dom, [dom.convert(x/2), dom.convert(3)])

    dom = QQ[x,y]

    assert construct_domain([x/2, 3*y]) == \
        (dom, [dom.convert(x/2), dom.convert(3*y)])

    dom = RR[x]

    assert construct_domain([x/2, 3.5]) == \
        (dom, [dom.convert(x/2), dom.convert(3.5)])

    dom = RR[x,y]

    assert construct_domain([x/2, 3.5*y]) == \
        (dom, [dom.convert(x/2), dom.convert(3.5*y)])

    dom = ZZ.frac_field(x)

    assert construct_domain([2/x, 3]) == \
        (dom, [dom.convert(2/x), dom.convert(3)])

    dom = ZZ.frac_field(x,y)

    assert construct_domain([2/x, 3*y]) == \
        (dom, [dom.convert(2/x), dom.convert(3*y)])

    assert construct_domain(2) == (ZZ, ZZ(2))
    assert construct_domain(S(2)/3) == (QQ, QQ(2, 3))

def test_composite_option():
    assert construct_domain({(1,): sin(y)}, composite=False) == \
        (EX, {(1,): EX(sin(y))})

    assert construct_domain({(1,): y}, composite=False) == \
        (EX, {(1,): EX(y)})

    assert construct_domain({(1, 1): 1}, composite=False) == \
        (ZZ, {(1, 1): 1})

    assert construct_domain({(1, 0): y}, composite=False) == \
        (EX, {(1, 0): EX(y)})
