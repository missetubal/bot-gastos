import unittest
from unittest.mock import MagicMock, patch
from supabase import Client  # Importar para tipagem do mock
import uuid  # Para simular IDs UUID

# Importar o módulo db para testar suas funções
from src.core import db

class TestDatabase(unittest.TestCase):
    def setUp(self):
        # Mock do cliente Supabase para todos os testes
        self.mock_supabase_client = MagicMock(spec=Client)

        # Criamos um mock para o retorno de .execute()
        self.mock_execute = MagicMock()

        # Criamos um mock que representará o objeto retornado por .table("...")
        # Este mock terá todos os métodos encadeáveis (insert, select, update, delete, eq, order, limit)
        self.mock_table_methods = MagicMock()

        # Configuramos os métodos encadeáveis para retornar o próprio mock_table_methods
        # para que possamos encadear chamadas como .select().eq().order().execute()
        self.mock_table_methods.insert.return_value = self.mock_table_methods
        self.mock_table_methods.select.return_value = self.mock_table_methods
        self.mock_table_methods.update.return_value = self.mock_table_methods
        self.mock_table_methods.delete.return_value = self.mock_table_methods
        self.mock_table_methods.eq.return_value = self.mock_table_methods
        self.mock_table_methods.order.return_value = self.mock_table_methods
        self.mock_table_methods.limit.return_value = self.mock_table_methods

        # Configuramos o método .execute() para retornar o mock_execute
        self.mock_table_methods.execute.return_value = self.mock_execute

        # Finalmente, configuramos supabase_client.table() para retornar o mock_table_methods
        self.mock_supabase_client.table.return_value = self.mock_table_methods
        
        # Valores de retorno padrão para o .execute() (para que a maioria dos testes passe por default)
        # Estes são os retornos do self.mock_execute (que é o que execute() retorna)
        self.mock_execute.return_value = MagicMock(data=[]) # Default para lista vazia (para select)

    # --- Testes para add_expense ---
    def test_add_expense_success_full_data(self):
        # Simula uma resposta de sucesso do Supabase (retorna dados inseridos)
        mock_response_data = [{'id': str(uuid.uuid4()), 'value': 150.0, 'category_id': str(uuid.uuid4()), 
                               'date': '2025-07-10', 'payment_method_id': str(uuid.uuid4()), 'description': 'Jantar'}]
        # Configure o retorno do execute() do mock_table_methods.insert
        self.mock_execute.return_value = MagicMock(data=mock_response_data)
        
        # IDs de exemplo
        test_category_id = str(uuid.uuid4())
        test_payment_method_id = str(uuid.uuid4())

        result = db.add_expense( # Chama sua função add_expense
            self.mock_supabase_client,
            value=150.0,
            category_id=test_category_id,
            date="2025-07-10",
            payment_method_id=test_payment_method_id,
            description="Jantar com amigos"
        )
        self.assertTrue(result) # Espera que a função retorne True
        
        # Verifica se 'table' foi chamado com 'expenses'
        self.mock_supabase_client.table.assert_called_with('expenses') 
        # Verifica se 'insert' foi chamado NO MOCK RETORNADO POR TABLE()
        self.mock_table_methods.insert.assert_called_once() 
        
        # Verifica os argumentos passados para insert
        args, kwargs = self.mock_table_methods.insert.call_args
        inserted_data = args[0]
        self.assertEqual(inserted_data['value'], 150.0)
        self.assertEqual(inserted_data['category_id'], test_category_id)
        self.assertEqual(inserted_data['date'], "2025-07-10")
        self.assertEqual(inserted_data['payment_method_id'], test_payment_method_id)
        self.assertEqual(inserted_data['description'], "Jantar com amigos")

    def test_add_expense_success_minimal_data(self):
        mock_response_data = [{'id': str(uuid.uuid4()), 'value': 25.0, 'category_id': str(uuid.uuid4()), 'date': '2025-07-11'}]
        self.mock_execute.return_value = MagicMock(data=mock_response_data)
        
        test_category_id = str(uuid.uuid4())

        result = db.add_expense( # Chama sua função add_expense
            self.mock_supabase_client,
            value=25.0,
            category_id=test_category_id,
            date="2025-07-11"
        )
        self.assertTrue(result)
        self.mock_table_methods.insert.assert_called_once()
        args, kwargs = self.mock_table_methods.insert.call_args
        inserted_data = args[0]
        self.assertIsNone(inserted_data['payment_method_id'])
        self.assertIsNone(inserted_data['description'])

    def test_add_expense_failure(self):
        self.mock_table_methods.insert.return_value.execute.side_effect = Exception("Database connection error")
        
        result = db.add_expense( # Chama sua função add_expense
            self.mock_supabase_client,
            value=50.0,
            category_id=str(uuid.uuid4()),
            date="2025-07-12"
        )
        self.assertFalse(result)
        self.mock_table_methods.insert.assert_called_once()


    # --- Testes para get_gastos ---
    def test_get_gastos_empty(self):
        self.mock_table_methods.select.return_value.order.return_value.execute.return_value = MagicMock(data=[])
        gastos = db.get_gastos(self.mock_supabase_client)
        self.assertEqual(gastos, [])

    def test_get_gastos_with_data(self):
        mock_data = [
            {
                "value": 50.0,
                "category_id": "cat1",
                "date": "2025-07-01",
                "description": "Cafe",
                "payment_methods": {"name": "Pix"},
                "categories": {"name": "Alimentacao"},
            },
        ]
        self.mock_table_methods.select.return_value.order.return_value.execute.return_value = MagicMock(data=mock_data)
        
        gastos = db.get_gastos(self.mock_supabase_client)
        self.assertEqual(len(gastos), 1)
        self.assertEqual(gastos[0]["value"], 50.0)
        self.assertEqual(gastos[0]["categoria_nome"], "Alimentacao")
        self.assertEqual(gastos[0]["forma_pagamento_nome"], "Pix")
        self.assertNotIn("categories", gastos[0])

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
        self.mock_table_methods.select.return_value.order.return_value.execute.return_value.data = []
        ganhos = db.get_ganhos(self.mock_supabase_client)
        self.assertEqual(ganhos, [])

    # --- Testes para add_categoria ---
    # @patch(
    #     "src.utils.text_utils.to_camel_case", side_effect=lambda x: x.replace(" ", "")
    # )  # Mock to_camel_case
    # def test_add_categoria_success(self, mock_to_camel_case):
    #     self.mock_table_methods.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    #     # no existing category check
    #     self.mock_table_methods.insert.return_value.execute.return_value = MagicMock(
    #         data=[{"id": "cat-id-123"}]
    #     )  # after insert

    #     result = db.add_category(
    #         self.mock_supabase_client, "nova categoria", 500.0, ["nova", "cat"]
    #     )
    #     self.assertTrue(result)
    #     self.mock_supabase_client.table.assert_called_with("categories")
    #     self.mock_table_methods.insert.assert_called_once()
    #     args, _ = self.mock_table_methods.insert.call_args
    #     self.assertEqual(args[0]["name"], "NovaCategoria")

    @patch(
        "src.utils.text_utils.to_camel_case", side_effect=lambda x: x.replace(" ", "")
    )
    def test_add_categoria_exists(self, mock_to_camel_case):
        self.mock_table_methods.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "cat-id-existing"}]
        )  # Category exists
        result = db.add_category(self.mock_supabase_client, "existente", 100.0)
        self.assertFalse(result)

    # --- Testes para get_categorias ---
    def test_get_categorias_empty(self):
        self.mock_table_methods.select.return_value.order.return_value.execute.return_value.data = []
        categorias = db.get_categories(self.mock_supabase_client)
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
        categorias = db.get_categories(self.mock_supabase_client)
        self.assertEqual(len(categorias), 2)
        self.assertEqual(categorias[0]["nome"], "Alimentacao")

    # --- Testes para get_categoria_id_by_text ---
    @patch("src.core.db.get_categories")
    @patch(
        "src.utils.text_utils.to_camel_case",
        side_effect=lambda x: "".join(word.capitalize() for word in x.split()),
    )
    def test_get_categoria_id_by_text_exact_name(
        self, mock_to_camel_case, mock_get_categorias
    ):
        mock_get_categorias.return_value = [
            {"id": "cat1", "name": "Alimentacao", "aliases": []}
        ]
        cat_id = db.get_category_id_by_text(self.mock_supabase_client, "Alimentacao")
        self.assertEqual(cat_id, "cat1")

    @patch("src.core.db.get_categories")
    @patch(
        "src.utils.text_utils.to_camel_case",
        side_effect=lambda x: "".join(word.capitalize() for word in x.split()),
    )
    def test_get_categoria_id_by_text_alias(
        self, mock_to_camel_case, mock_get_categorias
    ):
        mock_get_categorias.return_value = [
            {"id": "cat1", "name": "Alimentacao", "aliases": ["mercado", "comida"]}
        ]
        cat_id = db.get_category_id_by_text(self.mock_supabase_client, "mercado")
        self.assertEqual(cat_id, "cat1")

    @patch("src.core.db.get_categories")
    @patch(
        "src.utils.text_utils.to_camel_case",
        side_effect=lambda x: "".join(word.capitalize() for word in x.split()),
    )
    def test_get_categoria_id_by_text_not_found(
        self, mock_to_camel_case, mock_get_categorias
    ):
        mock_get_categorias.return_value = [
            {"id": "cat1", "name": "Alimentacao", "aliases": []}
        ]
        cat_id = db.get_category_id_by_text(self.mock_supabase_client, "Inexistente")
        self.assertIsNone(cat_id)

    # --- Testes para get_formas_pagamento ---
    def test_get_formas_pagamento_empty(self):
        self.mock_table_methods.select.return_value.order.return_value.execute.return_value.data = []
        formas = db.get_payment_methods(self.mock_supabase_client)
        self.assertEqual(formas, [])

    def test_get_formas_pagamento_with_data(self):
        mock_data = [{"id": "fp1", "name": "Pix"}, {"id": "fp2", "name": "Credito"}]
        self.mock_table_methods.select.return_value.order.return_value.execute.return_value.data = mock_data
        formas = db.get_payment_methods(self.mock_supabase_client)
        self.assertEqual(len(formas), 2)
        self.assertEqual(formas[0]["name"], "Pix")

    # --- Testes para get_payment_method_id_by_name ---
    def test_get_payment_method_id_by_name_success(self):
        self.mock_table_methods.select.return_value.execute.return_value.data = [
            {"id": "fp1", "name": "Pix"}
        ]
        fp_id = db.get_payment_method_id_by_name(self.mock_supabase_client, "Pix")
        self.assertEqual(fp_id, "fp1")

    def test_get_payment_method_id_by_name_case_insensitive(self):
        self.mock_table_methods.select.return_value.execute.return_value.data = [
            {"id": "fp1", "name": "Pix"}
        ]
        fp_id = db.get_payment_method_id_by_name(self.mock_supabase_client, "pix")
        self.assertEqual(fp_id, "fp1")

    def test_get_payment_method_id_by_name_not_found(self):
        self.mock_table_methods.select.return_value.execute.return_value.data = []
        fp_id = db.get_payment_method_id_by_name(self.mock_supabase_client, "Bitcoin")
        self.assertIsNone(fp_id)

    # --- Testes para update_categoria_limite ---
    def test_update_categoria_limite_success(self):
        self.mock_table_methods.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "cat1", "monthly_limit": 100.0}]
        )
        result = db.update_categoria_limite(self.mock_supabase_client, "cat1", 100.0)
        self.assertTrue(result)

    # --- Testes para update_categoria_aliases ---
    def test_update_categoria_aliases_success(self):
        self.mock_table_methods.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "cat1", "aliases": ["alias1"]}]
        )
        result = db.update_category_aliases(
            self.mock_supabase_client, "cat1", ["alias1"]
        )
        self.assertTrue(result)
