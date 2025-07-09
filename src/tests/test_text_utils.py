# tests/test_text_utils.py
import unittest
from src.utils.text_utils import to_camel_case


class TestTextUtils(unittest.TestCase):
    def test_empty_string(self):
        self.assertEqual(to_camel_case(""), "")

    def test_single_word(self):
        self.assertEqual(to_camel_case("hello"), "Hello")
        self.assertEqual(to_camel_case("World"), "World")

    def test_multiple_words_space(self):
        self.assertEqual(to_camel_case("hello world"), "HelloWorld")
        self.assertEqual(to_camel_case("minha nova categoria"), "MinhaNovaCategoria")

    def test_multiple_words_hyphen(self):
        self.assertEqual(to_camel_case("hello-world"), "HelloWorld")
        self.assertEqual(to_camel_case("compra-online"), "CompraOnline")

    def test_multiple_words_underscore(self):
        self.assertEqual(to_camel_case("hello_world"), "HelloWorld")
        self.assertEqual(to_camel_case("valor_total"), "ValorTotal")

    def test_mixed_separators(self):
        self.assertEqual(
            to_camel_case("test-mixed_separators and_more"),
            "TestMixedSeparatorsAndMore",
        )

    def test_leading_trailing_spaces(self):
        self.assertEqual(
            to_camel_case("  leading and trailing  "), "LeadingAndTrailing"
        )

    def test_numbers_in_string(self):
        self.assertEqual(to_camel_case("item 123 for sale"), "Item123ForSale")

    # def test_already_camel_case(self):
    #     self.assertEqual(to_camel_case("AlreadyCamelCase"), "AlreadyCamelCase")

    def test_acronyms(self):
        # to_camel_case capitaliza cada palavra, então acrônimos podem não ficar como o esperado se forem minúsculas.
        # Ex: "tv purchase" -> "TvPurchase", não "TVPurchase". Isso depende do comportamento desejado.
        self.assertEqual(to_camel_case("tv purchase"), "TvPurchase")
        self.assertEqual(
            to_camel_case("TV purchase"), "TVPurchase"
        )  # Se já vier capitalizado
