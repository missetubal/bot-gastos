# build.sh
#!/usr/bin/env bash

# Força a instalação do pyenv para gerenciar versões de Python
curl https://pyenv.run | bash

# Adiciona pyenv ao PATH (para que o Render o encontre)
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"

# Instala a versão específica do Python (ex: 3.12.0)
pyenv install 3.12.0
pyenv global 3.12.0

# Cria o virtualenv com a versão correta
python3.12 -m venv .venv
source .venv/bin/activate

# Instala as dependências
pip install -r requirements.txt

echo "Finished custom build process."