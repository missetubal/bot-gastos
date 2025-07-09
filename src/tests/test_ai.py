# tests/test_ai.py
import unittest
from unittest.mock import patch, MagicMock
import requests # Importar requests aqui
from src.core import ai
import json
import datetime

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

    @patch('requests.post')
    def test_ask_llama_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'response': 'Llama is here!'}
        mock_post.return_value = mock_response

        response = ai.ask_llama("Hello Llama")
        self.assertEqual(response, 'Llama is here!')
        mock_post.assert_called_once_with(
            ai.OLLAMA_API_URL,
            headers={"Content-Type": "application/json"},
            data=json.dumps({"model": ai.OLLAMA_MODEL, "prompt": "Hello Llama", "stream": False})
        )

    @patch('requests.post')
    def test_ask_llama_failure(self, mock_post):
        mock_post.side_effect = requests.exceptions.RequestException("Connection error")
        response = ai.ask_llama("Hello Llama")
        self.assertEqual(response, 'Desculpe, não consegui processar sua requisição agora. O Llama está offline ou o modelo não está disponível?')

    # --- Testes para extract_transaction_info ---
    @patch('src.core.ai.ask_llama')
    def test_extract_transaction_info_gasto_completo(self, mock_ask_llama):
        mock_ask_llama.return_value = f'{{"intencao": "gasto", "valor": 50.0, "categoria": "Mercado", "data": "{self.today_str}", "forma_pagamento": "pix", "descricao_gasto": "Compras no mercado"}}'
        info = ai.extract_transaction_info("gastei 50 no mercado no pix")
        self.assertIsNotNone(info)
        self.assertEqual(info['intencao'], 'gasto')
        self.assertEqual(info['value'], 50.0)
        self.assertEqual(info['categoria'], 'Mercado')
        self.assertEqual(info['date'], self.today_str)
        self.assertEqual(info['forma_pagamento'], 'pix')
        self.assertEqual(info['descricao_gasto'], 'Compras no mercado')

    @patch('src.core.ai.ask_llama')
    def test_extract_transaction_info_ganho(self, mock_ask_llama):
        mock_ask_llama.return_value = f'{{"intencao": "ganho", "valor": 1000.0, "descricao": "Salário", "data": "{self.last_month_end_str}"}}'
        info = ai.extract_transaction_info("recebi meu salário de 1000 mês passado")
        self.assertIsNotNone(info)
        self.assertEqual(info['intencao'], 'ganho')
        self.assertEqual(info['value'], 1000.0)
        self.assertEqual(info['description'], 'Salário')
        self.assertEqual(info['date'], self.last_month_end_str)

    @patch('src.core.ai.ask_llama')
    def test_extract_transaction_info_adicionar_categoria(self, mock_ask_llama):
        mock_ask_llama.return_value = '{"intencao": "adicionar_categoria", "categoria_nome": "Lazer", "monthly_limit": 300.0}'
        info = ai.extract_transaction_info("adicione categoria lazer com limite de 300")
        self.assertIsNotNone(info)
        self.assertEqual(info['intencao'], 'adicionar_categoria')
        self.assertEqual(info['categoria_nome'], 'Lazer')
        self.assertEqual(info['monthly_limit'], 300.0)

    @patch('src.core.ai.ask_llama')
    def test_extract_transaction_info_grafico_categoria_com_filtro(self, mock_ask_llama):
        mock_ask_llama.return_value = f'{{"intencao": "mostrar_grafico_gastos_categoria", "forma_pagamento": "crédito", "data_inicio": "{self.current_month_start_str}", "data_fim": "{self.current_month_end_str}"}}'
        info = ai.extract_transaction_info("gastos por categoria no crédito este mês")
        self.assertIsNotNone(info)
        self.assertEqual(info['intencao'], 'mostrar_grafico_gastos_categoria')
        self.assertEqual(info['forma_pagamento'], 'crédito')
        self.assertEqual(info['data_inicio'], self.current_month_start_str)
        self.assertEqual(info['data_fim'], self.current_month_end_str)

    @patch('src.core.ai.ask_llama')
    def test_extract_transaction_info_invalid_json(self, mock_ask_llama):
        mock_ask_llama.return_value = '{"intencao": "gasto", "valor": 50, "categoria": "Mercado" // comentario}' # Invalid JSON
        info = ai.extract_transaction_info("gastei 50 mercado")
        self.assertIsNone(info)

    @patch('src.core.ai.ask_llama')
    def test_extract_transaction_info_no_json(self, mock_ask_llama):
        mock_ask_llama.return_value = 'Não entendi sua mensagem.'
        info = ai.extract_transaction_info("bla bla bla")
        self.assertIsNone(info)

    @patch('src.core.ai.ask_llama')
    def test_extract_transaction_info_value_as_string_comma(self, mock_ask_llama):
        mock_ask_llama.return_value = '{"intencao": "gasto", "valor": "18,50", "categoria": "Transporte", "data": "2025-07-07", "forma_pagamento": "débito", "descricao_gasto": "Corrida"}'
        info = ai.extract_transaction_info("gastei 18,50 no debito")
        self.assertIsNotNone(info)
        self.assertEqual(info['value'], 18.50)

    # --- Testes para suggest_category_from_llama ---
    @patch('src.core.ai.ask_llama')
    def test_suggest_category_from_llama_success(self, mock_ask_llama):
        mock_ask_llama.return_value = 'Transporte'
        categories = ['Alimentacao', 'Transporte', 'Lazer']
        suggestion = ai.suggest_category_from_llama("ônibus", categories)
        self.assertEqual(suggestion, 'Transporte')

    @patch('src.core.ai.ask_llama')
    def test_suggest_category_from_llama_no_suggestion(self, mock_ask_llama):
        mock_ask_llama.return_value = 'NENHUMA'
        categories = ['Alimentacao', 'Lazer']
        suggestion = ai.suggest_category_from_llama("algo muito estranho", categories)
        self.assertIsNone(suggestion)

    @patch('src.core.ai.ask_llama')
    def test_suggest_category_from_llama_invalid_suggestion(self, mock_ask_llama):
        mock_ask_llama.return_value = 'CategoriaInvalida' # Not in existing_categories
        categories = ['Alimentacao', 'Lazer']
        suggestion = ai.suggest_category_from_llama("termo", categories)
        self.assertIsNone(suggestion)