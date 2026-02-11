# systemd deployment

## Bot runner (always on)

1) Copy service file:

- `sudo mkdir -p /etc/systemd/system`
- `sudo cp deploy/systemd/election-bot-runner.service /etc/systemd/system/election-bot-runner.service`

2) Adjust paths inside the service:

- `WorkingDirectory` should point to your `backend/` folder on the server.
- `ExecStart` should use your server python or virtualenv python.

3) Enable + start:

- `sudo systemctl daemon-reload`
- `sudo systemctl enable --now election-bot-runner`

4) Logs:

- `sudo journalctl -u election-bot-runner -f`

## Notes

- Only **one** bot runner must poll Telegram per token. Multiple instances cause `409 Conflict` and make the bot stop responding.
- The runner includes a lock file (`backend/.bot_runner.lock`) to prevent double-start on a single host.
