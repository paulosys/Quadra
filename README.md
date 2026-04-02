# QUADRA — Multiplayer Ball Game

Jogo web multiplayer para até 4 jogadores, com física real no servidor.

## Estrutura

```
quadra/
├── server.py          ← servidor WebSocket (física autoritativa)
├── index.html         ← cliente do jogo (browser)
├── entrypoint.py      ← inicia HTTP + WebSocket juntos
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## Como subir com Docker

### 1. Copie os arquivos para o servidor

```bash
scp -r ./quadra usuario@seu-servidor:/home/usuario/quadra
```

### 2. No servidor, suba com Docker Compose

```bash
cd /home/usuario/quadra
docker compose up -d --build
```

Pronto! O jogo estará rodando.

## Como acessar

- Página do jogo: `http://IP-DO-SERVIDOR:8080`
- WebSocket (interno): `ws://IP-DO-SERVIDOR:8765`

Todos os jogadores acessam `http://IP-DO-SERVIDOR:8080` no browser.

## Firewall

Certifique-se de que as portas estão abertas:

```bash
# Ubuntu / ufw
sudo ufw allow 8080/tcp
sudo ufw allow 8765/tcp
sudo ufw reload
```

## Como jogar

1. Cada jogador acessa `http://IP:8080` no browser
2. Digite seu nome
3. **Criador da sala**: deixe o campo de sala em branco → será gerado um código aleatório
4. **Outros jogadores**: digitem o mesmo código de sala
5. Quando todos entrarem, o criador clica **INICIAR JOGO**

### Controles

| Posição    | Teclas            |
|------------|-------------------|
| Topo       | `A` / `D`         |
| Baixo      | `←` / `→`         |
| Esquerda   | `W` / `S`         |
| Direita    | `↑` / `↓`         |

Em mobile: botões ◀ ▶ aparecem automaticamente.

## Gerenciamento do container

```bash
# Ver logs ao vivo
docker compose logs -f

# Parar
docker compose down

# Reiniciar
docker compose restart

# Ver status
docker compose ps
```

## Rodar sem Docker (direto no servidor)

```bash
pip install websockets==12.0 aiohttp
python entrypoint.py
```

## Notas técnicas

- A física roda **no servidor** (autoritativa) a 60 ticks/s
- O cliente faz interpolação suave para esconder latência
- Múltiplas salas simultâneas são suportadas (cada sala tem código único)
- Salas são destruídas automaticamente quando todos saem
