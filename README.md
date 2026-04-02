# ⚡ WakeSettings Bot V2

> All-in-one Discord bot for `.gg/wakesettings` — Verify + Full Ticket System  
> Built with discord.py 2 | Railway-ready | Python 3.12+

---

## 📁 Project Structure

```
wakesettings-bot/
├── bot.py                  # Entry point — loads cogs
├── cogs/
│   ├── verify.py           # Verification system
│   └── tickets.py          # Full ticket system
├── utils/
│   └── transcript.py       # Transcript generator
├── data/
│   └── tickets.json        # Auto-generated: ticket counter & state
├── banner.png              # Server banner (used in embeds)
├── requirements.txt
├── Procfile                # Railway entrypoint
├── nixpacks.toml           # Pins Python 3.12 on Railway
├── .env.example            # Environment variable template
└── .gitignore
```

---

## 🎫 Ticket System Features

| Feature | Details |
|---|---|
| **5 Categories** | Support, Script Kaufen, Commission, Report, Staff Bewerbung |
| **Modal Forms** | Each category has 2–3 custom questions (Discord Modal popup) |
| **Private Channels** | One channel per ticket, hidden from everyone else |
| **One ticket limit** | Users can only have 1 open ticket per category |
| **Ticket counter** | Channels named `ticket-0001-username` |
| **Claim system** | Staff claims ticket → channel renamed to `claimed-0001-staffname` |
| **Transcript** | `.txt` file generated on close, sent to transcript channel + user DM |
| **Auto-close** | Configurable inactivity timeout (default: 24h) |
| **Full logging** | Every action logged to log channel |
| **Persistent views** | Buttons survive bot restarts |
| **Stats command** | `/ticketstats` shows open tickets per category |

---

## 🚀 Setup

### Step 1 — Discord Developer Portal
1. Go to [discord.dev/applications](https://discord.com/developers/applications)
2. Create app → **Bot** tab → **Reset Token** → copy it
3. Enable **Privileged Intents**: `SERVER MEMBERS INTENT` + `MESSAGE CONTENT INTENT`
4. **OAuth2 → URL Generator**:
   - Scopes: `bot` + `applications.commands`
   - Permissions: `Manage Channels`, `Manage Roles`, `Send Messages`, `Embed Links`, `Attach Files`, `Read Message History`, `View Channels`
5. Invite bot with the generated URL

### Step 2 — Configure .env
```bash
cp .env.example .env
```
Fill in all IDs. Enable Developer Mode in Discord (Settings → Advanced) to right-click and Copy IDs.

**Required IDs:**
- `DISCORD_TOKEN` → From step 1
- `GUILD_ID` → Right-click your server → Copy Server ID
- `VERIFIED_ROLE_ID` → Right-click your Verified role → Copy Role ID
- `TICKET_CATEGORY_ID` → Right-click the channel category for tickets → Copy ID
- `SUPPORT_ROLE_ID` → Right-click your Staff/Support role → Copy Role ID
- `TRANSCRIPT_CHANNEL_ID` → Right-click transcript channel → Copy ID
- `LOG_CHANNEL_ID` → Right-click log channel → Copy ID

### Step 3 — Deploy on Railway
1. Push this folder to a GitHub repo
2. [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Select repo → **Variables** tab → add all values from `.env.example`
4. Railway auto-detects `Procfile` → deploys automatically
5. Bot comes online ✅

### Step 4 — Set up Discord server
1. In your server, go to the ticket channel and run `/sendtickets`
2. Go to the verify channel and run `/sendverify`
3. Done — both panels are live

---

## 🎮 Slash Commands

### Ticket System
| Command | Description | Permission |
|---|---|---|
| `/sendtickets` | Posts the ticket panel with category dropdown | Admin |
| `/closeticket` | Closes the current ticket (opens reason modal) | Manage Channels |
| `/addmember @user` | Adds a member to the current ticket | Manage Channels |
| `/ticketstats` | Shows ticket statistics per category | Admin |

### Verify System
| Command | Description | Permission |
|---|---|---|
| `/sendverify` | Posts the verification embed + button | Admin |
| `/unverify @member` | Removes Verified role from a member | Admin |

---

## 🔒 Security
- **Guild-lock** — bot auto-leaves unauthorized servers
- **Persistent buttons** — survive restarts via `custom_id`
- **One ticket per category** — prevents spam
- **Ephemeral responses** — private feedback to users
