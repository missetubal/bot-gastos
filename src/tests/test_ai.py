# tests/test_ai.py
import unittest
from unittest.mock import patch, MagicMock
import requests
import json
import datetime
from supabase import Client # Importar Client para tipagem do mock
from src.core import ai

class TestArtificialIntelligence(unittest.TestCase):

    def setUp(self):
        # Mocks para as datas no prompt
        self.today_str = datetime.date(2025, 7, 7).strftime("%Y-%m-%d")
        self.yesterday_str = (datetime.date(2025, 7, 7) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        self.two_days_ago_str = (datetime.date(2025, 7, 7) - datetime.timedelta(days=2)).strftime("%Y-%m-%d")
        self.last_week_day_str = (datetime.date(2025, 7, 7) - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        self.current_month_start_str = datetime.date(2025, 7, 1).strftime("%Y-%m-%d")
        self.current_month_end_str = datetime.date(2025, 7, 31).strftime("%Y-%m-%d") # Assumindo 31 dias para o mês
        self.last_month_start_str = datetime.date(2025, 6, 1).strftime("%Y-%m-%d")
        self.last_month_end_str = datetime.date(2025, 6, 30).strftime("%Y-%m-%d")

        # NOVO: Mock para o cliente Supabase
        self.mock_supabase_client = MagicMock(spec=Client)

    # @patch('requests.post')
    # def test_ask_llama_success(self, mock_post):
    #     mock_response = MagicMock()
    #     mock_response.raise_for_status.return_value = None
    #     mock_response.json.return_value = {'response': 'Llama is here!'}
    #     mock_post.return_value = mock_response

    #     response = ai.ask_llama("Hello Llama")
    #     self.assertEqual(response, 'Llama is here!')
    #     mock_post.assert_called_once_with(
    #         ai.OLLAMA_API_URL,
    #         headers={"Content-Type": "application/json"},
    #         data=json.dumps({"model": ai.OLLAMA_MODEL, "prompt": "Hello Llama", "stream": False})
    #     )

    @patch('requests.post')
    def test_ask_llama_failure(self, mock_post):
        mock_post.side_effect = requests.exceptions.RequestException("Connection error")
        response = ai.ask_llama("Hello Llama")
        self.assertEqual(response, "Desculpe, não consegui processar sua requisição agora. O modelo de IA está offline ou indisponível.")

    # --- Testes para extract_transaction_info ---
    @patch('src.core.ai.ask_llama') # Mock ask_llama aqui
    @patch('src.core.db.get_categories') # Mock get_categories para não chamar o DB real
    def test_extract_transaction_info_gasto_completo(self, mock_get_categories, mock_ask_llama):
        mock_get_categories.return_value = [{'name': 'Alimentacao'}, {'name': 'Transporte'}] # Exemplo de retorno
        mock_ask_llama.return_value = f'{{"intencao": "gasto", "valor": 50.0, "categoria": "Mercado", "data": "{self.today_str}", "forma_pagamento": "pix", "descricao_gasto": "Compras no mercado"}}'
        
        # Passa self.mock_supabase_client como o segundo argumento
        info = ai.extract_transaction_info("gastei 50 no mercado no pix", self.mock_supabase_client) 
        self.assertIsNotNone(info)
        self.assertEqual(info['intencao'], 'gasto')
        self.assertEqual(info['valor'], 50.0)
        self.assertEqual(info['categoria'], 'Mercado')
        self.assertEqual(info['data'], self.today_str)
        self.assertEqual(info['forma_pagamento'], 'pix')
        self.assertEqual(info['descricao_gasto'], 'Compras no mercado')
        mock_get_categories.assert_called_once_with(self.mock_supabase_client) # Verifica se get_categories foi chamado com o mock

    @patch('src.core.ai.ask_llama')
    @patch('src.core.db.get_categories')
    def test_extract_transaction_info_ganho(self, mock_get_categories, mock_ask_llama):
        mock_get_categories.return_value = [] # Ganhos não usam categorias
        mock_ask_llama.return_value = f'{{"intencao": "ganho", "valor": 1000.0, "descricao": "Salário", "data": "{self.last_month_end_str}"}}'
        info = ai.extract_transaction_info("recebi meu salário de 1000 mês passado", self.mock_supabase_client)
        self.assertIsNotNone(info)
        self.assertEqual(info['intencao'], 'ganho')
        self.assertEqual(info['valor'], 1000.0)
        self.assertEqual(info['descricao'], 'Salário')
        self.assertEqual(info['data'], self.last_month_end_str)

    @patch('src.core.ai.ask_llama')
    @patch('src.core.db.get_categories')
    def test_extract_transaction_info_adicionar_categoria(self, mock_get_categories, mock_ask_llama):
        mock_get_categories.return_value = []
        mock_ask_llama.return_value = '{"intencao": "adicionar_categoria", "categoria_nome": "Lazer", "limite_mensal": 300.0}'
        # Passa self.mock_supabase_client
        info = ai.extract_transaction_info("adicione categoria lazer com limite de 300", self.mock_supabase_client)
        self.assertIsNotNone(info)
        self.assertEqual(info['intencao'], 'adicionar_categoria')
        self.assertEqual(info['categoria_nome'], 'Lazer')
        self.assertEqual(info['limite_mensal'], 300.0)
        mock_get_categories.assert_called_once_with(self.mock_supabase_client)

    @patch('src.core.ai.ask_llama')
    @patch('src.core.db.get_categories')
    def test_extract_transaction_info_grafico_categoria_com_filtro(self, mock_get_categories, mock_ask_llama):
        mock_get_categories.return_value = [{'name': 'Alimentacao'}, {'name': 'Transporte'}]
        mock_ask_llama.return_value = f'{{"intencao": "mostrar_grafico_gastos_categoria", "forma_pagamento": "crédito", "data_inicio": "{self.current_month_start_str}", "data_fim": "{self.current_month_end_str}"}}'
        info = ai.extract_transaction_info("gastos por categoria no crédito este mês", self.mock_supabase_client)
        self.assertIsNotNone(info)
        self.assertEqual(info['intencao'], 'mostrar_grafico_gastos_categoria')
        self.assertEqual(info['forma_pagamento'], 'crédito')
        self.assertEqual(info['data_inicio'], self.current_month_start_str)
        self.assertEqual(info['data_fim'], self.current_month_end_str)
        mock_get_categories.assert_called_once_with(self.mock_supabase_client)

    @patch('src.core.ai.ask_llama')
    @patch('src.core.db.get_categories')
    def test_extract_transaction_info_invalid_json(self, mock_get_categories, mock_ask_llama):
        mock_get_categories.return_value = []
        mock_ask_llama.return_value = '{"intencao": "gasto", "valor": 50, "categoria": "Mercado" // comentario}' # Invalid JSON
        info = ai.extract_transaction_info("gastei 50 mercado", self.mock_supabase_client)
        self.assertIsNone(info)

    @patch('src.core.ai.ask_llama')
    @patch('src.core.db.get_categories')
    def test_extract_transaction_info_no_json(self, mock_get_categories, mock_ask_llama):
        mock_get_categories.return_value = []
        mock_ask_llama.return_value = 'Não entendi sua mensagem.'
        info = ai.extract_transaction_info("bla bla bla", self.mock_supabase_client)
        self.assertIsNone(info)

    @patch('src.core.ai.ask_llama')
    @patch('src.core.db.get_categories')
    # def test_extract_transaction_info_value_as_string_comma(self, mock_get_categorias, mock_ask_llama):
    #     mock_get_categorias.return_value = []
    #     mock_ask_llama.return_value = '{"intencao": "gasto", "valor": "18.50", "categoria": "Transporte", "data": "2025-07-07", "forma_pagamento": "débito", "descricao_gasto": "Corrida"}'
        
    #     info = ai.extract_transaction_info("gastei 18,50 no debito", self.mock_supabase_client)
    #     self.assertIsNotNone(info)
    #     self.assertEqual(info['valor'], 18.50) # Espera float
    #     self.assertEqual(info['forma_pagamento'], 'débito') # Verifica se outros campos estão corretos

    # --- Testes para suggest_category_from_llama ---
    # @patch('src.core.ai.ask_llama')
    # def test_suggest_category_from_llama_success(self, mock_ask_llama):
    #     mock_ask_llama.return_value = 'Transporte'
    #     categories = ['Alimentacao', 'Transporte', 'Lazer']
    #     # Passa self.mock_supabase_client
    #     suggestion = ai.suggest_category_from_llama("ônibus", categories, self.mock_supabase_client)
    #     self.assertEqual(suggestion, 'Transporte')

    @patch('src.core.ai.ask_llama')
    def test_suggest_category_from_llama_no_suggestion(self, mock_ask_llama):
        mock_ask_llama.return_value = 'NENHUMA'
        categories = ['Alimentacao', 'Lazer']
        # Passa self.mock_supabase_client
        suggestion = ai.suggest_category_from_llama("algo muito estranho", categories, self.mock_supabase_client)
        self.assertIsNone(suggestion)

    @patch('src.core.ai.ask_llama')
    def test_suggest_category_from_llama_invalid_suggestion(self, mock_ask_llama):
        mock_ask_llama.return_value = 'CategoriaInvalida' # Not in existing_categories
        categories = ['Alimentacao', 'Lazer']
        # Passa self.mock_supabase_client
        suggestion = ai.suggest_category_from_llama("termo", categories, self.mock_supabase_client)
        self.assertIsNone(suggestion)

    # --- Testes para extract_correction_from_llama ---
    @patch('src.core.ai.ask_llama')
    def test_extract_correction_from_llama_categoria(self, mock_ask_llama):
        mock_ask_llama.return_value = '{"campo": "categoria", "novo_valor": "Lazer"}'
        correction = ai.extract_correction_from_llama("Categoria Lazer")
        self.assertIsNotNone(correction)
        self.assertEqual(correction['campo'], 'categoria')
        self.assertEqual(correction['novo_valor'], 'Lazer')

    @patch('src.core.ai.ask_llama')
    def test_extract_correction_from_llama_valor(self, mock_ask_llama):
        mock_ask_llama.return_value = '{"campo": "valor", "novo_valor": "60.50"}'
        correction = ai.extract_correction_from_llama("Valor 60.50")
        self.assertIsNotNone(correction)
        self.assertEqual(correction['campo'], 'valor')
        self.assertEqual(correction['novo_valor'], 60.50)
    @patch('src.core.ai.ask_llama')
    def test_extract_correction_from_llama_data(self, mock_ask_llama):
        mock_ask_llama.return_value = '{"campo": "data", "novo_valor": "2025-07-01"}'
        correction = ai.extract_correction_from_llama("Data 2025-07-01")
        self.assertIsNotNone(correction)
        self.assertEqual(correction['campo'], 'data')
        self.assertEqual(correction['novo_valor'], '2025-07-01')

    @patch('src.core.ai.ask_llama')
    def test_extract_correction_from_llama_invalid_json(self, mock_ask_llama):
        mock_ask_llama.return_value = '{"campo": "valor", "novo_valor": "abc" // comentario}' # JSON inválido
        correction = ai.extract_correction_from_llama("Valor abc")
        self.assertIsNone(correction)