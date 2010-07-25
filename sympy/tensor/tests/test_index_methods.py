from sympy.tensor.indexed import Idx, Indexed, IndexedElement
from sympy.tensor.index_methods import get_contraction_structure, get_indices, IndexConformanceException
from sympy import symbols, S
from sympy.utilities.pytest import raises

def test_trivial_indices():
    x, y = symbols('x y')
    assert get_indices(x) == ((), ())
    assert get_indices(x*y) == ((), ())
    assert get_indices(x + y) == ((), ())
    assert get_indices(x**y) == ((), ())

def test_get_indices_IndexedElement():
    x = Indexed('x')
    y = Indexed('y')
    i, j = Idx('i'), Idx('j')
    assert get_indices(x(i, j)) == ((i, j), ())
    assert get_indices(x(j, i)) == ((j, i), ())

def test_get_indices_IndexedElement_nc():
    x = Indexed('x', commutative=False)
    y = Indexed('y', commutative=False)
    i, j = Idx('i'), Idx('j')
    assert get_indices(x(i, j)) == ((), (i, j))
    assert get_indices(x(j, i)) == ((), (j, i))

def test_get_indices_mul():
    x = Indexed('x')
    y = Indexed('y')
    i, j = Idx('i'), Idx('j')
    assert get_indices(x(j)*y(i)) == (tuple(sorted(([i, j]), key=hash)), ())
    assert get_indices(x(i)*y(j)) == (tuple(sorted(([i, j]), key=hash)), ())

def test_get_indices_mul_nc():
    x = Indexed('x', commutative=False)
    y = Indexed('y', commutative=False)
    z = Indexed('z', commutative=True)
    i, j, k = Idx('i'), Idx('j'), Idx('k')
    assert get_indices(x(j)*y(i)) == ((), (j, i))
    assert get_indices(x(i)*y(j)) == ((), (i, j))
    assert get_indices(x(i)*y(j)*z(k)) == ((k,), (i, j))

def test_get_indices_exceptions():
    x = Indexed('x')
    y = Indexed('y')
    i, j = Idx('i'), Idx('j')
    raises(IndexConformanceException, 'get_indices(x(i) + y(j))')
    raises(IndexConformanceException, 'get_indices(x(i) + y(i, i))')

def test_get_indices_add():
    x = Indexed('x')
    y = Indexed('y')
    A = Indexed('A')
    i, j, k = Idx('i'), Idx('j'), Idx('k')
    assert get_indices(x(i) + 2*y(i)) == ((i,), ())
    assert get_indices(y(i) + 2*A(i, j)*x(j)) == ((i,), ())
    assert get_indices(y(i) + 2*(x(i) + A(i, j)*x(j))) == ((i,), ())
    assert get_indices(y(i) + x(i)*(A(j, j) + 1)) == ((i,), ())
    assert get_indices(y(i) + x(i)*x(j)*(y(j) + A(j, k)*x(k))) == ((i,), ())

def test_get_indices_add_nc():
    x = Indexed('x', commutative=False)
    y = Indexed('y', commutative=False)
    A = Indexed('A', commutative=False)
    i, j, k = Idx('i'), Idx('j'), Idx('k')
    assert get_indices(x(i) + 2*y(i)) == ((), (i,))
    assert get_indices(y(i) + 2*A(i, j)*x(j)) == ((), (i,))
    assert get_indices(y(i) + 2*(x(i) + A(i, j)*x(j))) == ((), (i,))
    assert get_indices(y(i) + x(i)*(A(j, j) + 1)) == ((), (i,))
    assert get_indices(y(i) + x(i)*x(j)*(y(j) + A(j, k)*x(k))) == ((), (i,))

def test_get_contraction_structure_basic():
    x = Indexed('x')
    y = Indexed('y')
    i, j = Idx('i'), Idx('j')
    assert get_contraction_structure(x(i)*y(j)) == {None: set([x(i)*y(j)])}
    assert get_contraction_structure(x(i) + y(j)) == {None: set([x(i), y(j)])}
    assert get_contraction_structure(x(i)*y(i)) == {(i,): set([x(i)*y(i)])}
    assert get_contraction_structure(1 + x(i)*y(i)) == {None: set([S.One]), (i,): set([x(i)*y(i)])}

def test_get_contraction_structure_complex():
    x = Indexed('x')
    y = Indexed('y')
    A = Indexed('A')
    i, j, k = Idx('i'), Idx('j'), Idx('k')
    expr1 = y(i) + A(i, j)*x(j)
    d1 = {None: set([y(i)]), (j,): set([A(i, j)*x(j)])}
    assert get_contraction_structure(expr1) == d1
    expr2 = expr1*A(k, i) + x(k)
    d2 = {None: set([x(k)]), (i,): set([expr1*A(k, i)]), expr1*A(k, i): [d1]}
    assert get_contraction_structure(expr2) == d2