# tests/test_db.py
import unittest
from unittest.mock import MagicMock, patch
from src.core import db
from supabase import Client  # Importar para tipagem do mock
import uuid  # Para simular IDs UUID
# Importar Client para o spec


class TestDatabase(unittest.TestCase):
    def setUp(self):
        # Mock do cliente Supabase para todos os testes
        self.mock_supabase_client = MagicMock(spec=Client)

        # Configurar o mock para encadeamento de chamadas:
        # supabase.table('nome').insert({...}).execute()
        # supabase.table('nome').select(...).eq(...).order(...).execute()

        # O retorno de table() deve ser um mock que possui os métodos de CRUD (insert, select, etc.)
        # E o retorno de insert(), select(), eq(), order(), limit(), update() deve ser um mock que tem .execute()

        # Criamos um mock intermediário para representar o retorno de table()
        self.mock_table_methods = MagicMock()
        self.mock_supabase_client.table.return_value = self.mock_table_methods

        # Agora, definimos o encadeamento para os métodos de CRUD
        self.mock_table_methods.insert.return_value = MagicMock(execute=MagicMock())
        self.mock_table_methods.select.return_value = MagicMock(
            eq=MagicMock(
                return_value=MagicMock(
                    order=MagicMock(
                        return_value=MagicMock(
                            limit=MagicMock(
                                return_value=MagicMock(execute=MagicMock())
                            )  # Para limit().execute()
                        )
                    )
                )
            ),
            order=MagicMock(
                return_value=MagicMock(execute=MagicMock())
            ),  # Para select().order().execute()
        )
        self.mock_table_methods.update.return_value = MagicMock(
            eq=MagicMock(return_value=MagicMock(execute=MagicMock()))
        )

        # Default success response for execute()
        self.mock_table_methods.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": str(uuid.uuid4())}]
        )
        self.mock_table_methods.select.return_value.execute.return_value = MagicMock(
            data=[]
        )
        self.mock_table_methods.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        self.mock_table_methods.select.return_value.order.return_value.execute.return_value = MagicMock(
            data=[]
        )
        self.mock_table_methods.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{}]
        )  # Default para update

    # --- Testes para add_gasto ---
    def test_add_gasto_success(self):
        # Use o mock correto para a resposta do execute
        self.mock_table_methods.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": str(uuid.uuid4())}]
        )
        result = db.add_gasto(
            self.mock_supabase_client,
            100.0,
            str(uuid.uuid4()),
            "2025-07-01",
            str(uuid.uuid4()),
            "Compras no mercado",
        )
        self.assertTrue(result)
        self.mock_supabase_client.table.assert_called_with("gastos")
        self.mock_table_methods.insert.assert_called_once()  # Chama no mock_table_methods
        args, kwargs = (
            self.mock_table_methods.insert.call_args
        )  # Pega args do mock_table_methods.insert
        self.assertIn("valor", args[0])
        self.assertIn("categoria_id", args[0])
        self.assertIn("data", args[0])
        self.assertIn("forma_pagamento_id", args[0])
        self.assertIn("descricao", args[0])

    def test_add_gasto_failure(self):
        self.mock_table_methods.insert.return_value.execute.side_effect = Exception(
            "DB error"
        )  # Simula falha no execute
        result = db.add_gasto(
            self.mock_supabase_client, 100.0, str(uuid.uuid4()), "2025-07-01"
        )
        self.assertFalse(result)

    # --- Testes para get_gastos ---
    def test_get_gastos_empty(self):
        self.mock_table_methods.select.return_value.execute.return_value.data = []  # Mock para a chamada final execute()
        gastos = db.get_gastos(self.mock_supabase_client)
        self.assertEqual(gastos, [])

    def test_get_gastos_with_data(self):
        mock_data = [
            {
                "valor": 50.0,
                "categoria_id": "cat1",
                "data": "2025-07-01",
                "descricao": "Cafe",
                "formas_pagamento": {"nome": "Pix"},
                "categorias": {"nome": "Alimentacao"},
            },
        ]
        self.mock_table_methods.select.return_value.execute.return_value.data = (
            mock_data
        )
        gastos = db.get_gastos(self.mock_supabase_client)
        self.assertEqual(len(gastos), 1)
        self.assertEqual(gastos[0]["valor"], 50.0)
        self.assertEqual(gastos[0]["categoria_nome"], "Alimentacao")
        self.assertEqual(gastos[0]["forma_pagamento_nome"], "Pix")
        self.assertNotIn("categorias", gastos[0])

    # --- Testes para add_ganho ---
    def test_add_ganho_success(self):
        self.mock_table_methods.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": str(uuid.uuid4())}]
        )
        result = db.add_ganho(
            self.mock_supabase_client, 1000.0, "Salário", "2025-07-05"
        )
        self.assertTrue(result)
        self.mock_supabase_client.table.assert_called_with("ganhos")
        self.mock_table_methods.insert.assert_called_once()

    # --- Testes para get_ganhos ---
    def test_get_ganhos_empty(self):
        self.mock_table_methods.select.return_value.execute.return_value.data = []
        ganhos = db.get_ganhos(self.mock_supabase_client)
        self.assertEqual(ganhos, [])

    # --- Testes para add_categoria ---
    @patch(
        "src.utils.text_utils.to_camel_case", side_effect=lambda x: x.replace(" ", "")
    )  # Mock to_camel_case
    def test_add_categoria_success(self, mock_to_camel_case):
        self.mock_table_methods.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )  # no existing category check
        self.mock_table_methods.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "cat-id-123"}]
        )  # after insert

        result = db.add_categoria(
            self.mock_supabase_client, "nova categoria", 500.0, ["nova", "cat"]
        )
        self.assertTrue(result)
        self.mock_supabase_client.table.assert_called_with("categorias")
        self.mock_table_methods.insert.assert_called_once()
        args, _ = self.mock_table_methods.insert.call_args
        self.assertEqual(args[0]["nome"], "NovaCategoria")

    @patch(
        "src.utils.text_utils.to_camel_case", side_effect=lambda x: x.replace(" ", "")
    )
    def test_add_categoria_exists(self, mock_to_camel_case):
        self.mock_table_methods.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "cat-id-existing"}]
        )  # Category exists
        result = db.add_categoria(self.mock_supabase_client, "existente", 100.0)
        self.assertFalse(result)

    # --- Testes para get_categorias ---
    def test_get_categorias_empty(self):
        self.mock_table_methods.select.return_value.order.return_value.execute.return_value.data = []
        categorias = db.get_categorias(self.mock_supabase_client)
        self.assertEqual(categorias, [])

    def test_get_categorias_with_data(self):
        mock_data = [
            {
                "id": "cat1",
                "nome": "Alimentacao",
                "limite_mensal": 800.0,
                "aliases": ["food", "grocery"],
            },
            {
                "id": "cat2",
                "nome": "Transporte",
                "limite_mensal": None,
                "aliases": None,
            },
        ]
        self.mock_table_methods.select.return_value.order.return_value.execute.return_value.data = mock_data
        categorias = db.get_categorias(self.mock_supabase_client)
        self.assertEqual(len(categorias), 2)
        self.assertEqual(categorias[0]["nome"], "Alimentacao")

    # --- Testes para get_categoria_id_by_text ---
    @patch("src.core.db.get_categorias")
    @patch(
        "src.utils.text_utils.to_camel_case",
        side_effect=lambda x: "".join(word.capitalize() for word in x.split()),
    )
    def test_get_categoria_id_by_text_exact_name(
        self, mock_to_camel_case, mock_get_categorias
    ):
        mock_get_categorias.return_value = [
            {"id": "cat1", "nome": "Alimentacao", "aliases": []}
        ]
        cat_id = db.get_categoria_id_by_text(self.mock_supabase_client, "Alimentacao")
        self.assertEqual(cat_id, "cat1")

    @patch("src.core.db.get_categorias")
    @patch(
        "src.utils.text_utils.to_camel_case",
        side_effect=lambda x: "".join(word.capitalize() for word in x.split()),
    )
    def test_get_categoria_id_by_text_alias(
        self, mock_to_camel_case, mock_get_categorias
    ):
        mock_get_categorias.return_value = [
            {"id": "cat1", "nome": "Alimentacao", "aliases": ["mercado", "comida"]}
        ]
        cat_id = db.get_categoria_id_by_text(self.mock_supabase_client, "mercado")
        self.assertEqual(cat_id, "cat1")

    @patch("src.core.db.get_categorias")
    @patch(
        "src.utils.text_utils.to_camel_case",
        side_effect=lambda x: "".join(word.capitalize() for word in x.split()),
    )
    def test_get_categoria_id_by_text_not_found(
        self, mock_to_camel_case, mock_get_categorias
    ):
        mock_get_categorias.return_value = [
            {"id": "cat1", "nome": "Alimentacao", "aliases": []}
        ]
        cat_id = db.get_categoria_id_by_text(self.mock_supabase_client, "Inexistente")
        self.assertIsNone(cat_id)

    # --- Testes para get_formas_pagamento ---
    def test_get_formas_pagamento_empty(self):
        self.mock_table_methods.select.return_value.order.return_value.execute.return_value.data = []
        formas = db.get_formas_pagamento(self.mock_supabase_client)
        self.assertEqual(formas, [])

    def test_get_formas_pagamento_with_data(self):
        mock_data = [{"id": "fp1", "nome": "Pix"}, {"id": "fp2", "nome": "Credito"}]
        self.mock_table_methods.select.return_value.order.return_value.execute.return_value.data = mock_data
        formas = db.get_formas_pagamento(self.mock_supabase_client)
        self.assertEqual(len(formas), 2)
        self.assertEqual(formas[0]["nome"], "Pix")

    # --- Testes para get_forma_pagamento_id_by_name ---
    def test_get_forma_pagamento_id_by_name_success(self):
        self.mock_table_methods.select.return_value.execute.return_value.data = [
            {"id": "fp1", "nome": "Pix"}
        ]
        fp_id = db.get_forma_pagamento_id_by_name(self.mock_supabase_client, "Pix")
        self.assertEqual(fp_id, "fp1")

    def test_get_forma_pagamento_id_by_name_case_insensitive(self):
        self.mock_table_methods.select.return_value.execute.return_value.data = [
            {"id": "fp1", "nome": "Pix"}
        ]
        fp_id = db.get_forma_pagamento_id_by_name(self.mock_supabase_client, "pix")
        self.assertEqual(fp_id, "fp1")

    def test_get_forma_pagamento_id_by_name_not_found(self):
        self.mock_table_methods.select.return_value.execute.return_value.data = []
        fp_id = db.get_forma_pagamento_id_by_name(self.mock_supabase_client, "Bitcoin")
        self.assertIsNone(fp_id)

    # --- Testes para update_categoria_limite ---
    def test_update_categoria_limite_success(self):
        self.mock_table_methods.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "cat1", "limite_mensal": 100.0}]
        )
        result = db.update_categoria_limite(self.mock_supabase_client, "cat1", 100.0)
        self.assertTrue(result)

    # --- Testes para update_categoria_aliases ---
    def test_update_categoria_aliases_success(self):
        self.mock_table_methods.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "cat1", "aliases": ["alias1"]}]
        )
        result = db.update_categoria_aliases(
            self.mock_supabase_client, "cat1", ["alias1"]
        )
        self.assertTrue(result)
