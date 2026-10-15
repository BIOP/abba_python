import pytest

from abba_python.abba import _dependencies, get_java_dependencies


def test_extra_dependencies_come_after_abba():
    # The first coordinate decides the transitive versions: it must stay ImageToAtlasRegister
    dependencies = _dependencies(['sc.fiji:fiji-llm:0.1.0'])
    assert dependencies[0].startswith('ch.epfl.biop:ImageToAtlasRegister:')
    assert dependencies == [*get_java_dependencies(), 'sc.fiji:fiji-llm:0.1.0']


def test_no_extra_dependencies():
    assert _dependencies(()) == get_java_dependencies()


def test_extra_dependencies_string_is_refused():
    # A string would be read as one coordinate per character
    with pytest.raises(TypeError):
        _dependencies('sc.fiji:fiji-llm:0.1.0')
