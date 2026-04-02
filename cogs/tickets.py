import discord
from discord.ext import commands, tasks
from discord import app_commands
import os, json, asyncio, traceback, logging
from datetime import datetime, timezone, timedelta
from utils.transcript import generate_transcript

logger = logging.getLogger("amate.tickets")

GUILD_ID              = int(os.getenv("GUILD_ID", "0"))
TICKET_CATEGORY_ID    = 1461398310278664260
SUPPORT_ROLE_ID       = 1461100758241120277
BOT_ACCESS_ROLE_ID    = 1489037952125370408
LOG_CHANNEL_ID        = int(os.getenv("LOG_CHANNEL_ID", "0"))
TRANSCRIPT_CHANNEL_ID = 1461398559298425035
AUTO_CLOSE_HOURS      = int(os.getenv("AUTO_CLOSE_HOURS", "24"))

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tickets.json")
BANNER    = os.path.join(os.path.dirname(os.path.dirname(__file__)), "banner.jpg")

CATEGORIES = {
    "support": {
        "label":       "🔧 Support",
        "description": "Allgemeiner Support & Hilfe",
        "emoji":       "🔧",
        "color":       0x7B2FBE,
        "questions": [
            ("Beschreibe dein Problem", "Was ist dein Problem? Sei so genau wie möglich.", True),
            ("Was hast du bereits versucht?", "Hast du schon etwas versucht um das Problem zu lösen?", False),
        ],
    },
    "kaufen": {
        "label":       "🛒 Script Kaufen",
        "description": "FiveM Script kaufen oder anfragen",
        "emoji":       "🛒",
        "color":       0x9B59B6,
        "questions": [
            ("Welches Script interessiert dich?", "z.B. HUD, Inventory, Garage, Custom...", True),
            ("Dein Budget (EUR)?", "Wie viel bist du bereit auszugeben?", True),
            ("Discord-Tag / Kontakt", "Dein Discord oder weitere Kontaktinfos", False),
        ],
    },
    "ident": {
        "label":       "🪪 Ident",
        "description": "Identität, Branding & Custom Identity",
        "emoji":       "🪪",
        "color":       0xA855F7,
        "questions": [
            ("Was soll gebrandet werden?", "Beschreibe dein Projekt oder deinen Server.", True),
            ("Referenzen / Inspirationen", "Hast du Beispiele oder Referenzen? (optional)", False),
            ("Budget & Deadline (EUR/Datum)", "z.B. 80 EUR bis 20. April 2026", True),
        ],
    },
    "design": {
        "label":       "🎨 Design",
        "description": "Grafik, UI & individuelle Designs",
        "emoji":       "🎨",
        "color":       0xC084FC,
        "questions": [
            ("Was soll designed werden?", "Logo, Banner, UI, Thumbnail etc. beschreibe es genau.", True),
            ("Referenzen / Inspirationen", "Links zu Beispielen oder aehnlichen Designs (optional)", False),
            ("Budget & Deadline (EUR/Datum)", "z.B. 50 EUR bis 10. April 2026", True),
        ],
    },
    "media": {
        "label":       "📷 Werde Amate Media",
        "description": "Bewirb dich als Amate Media Creator",
        "emoji":       "📷",
        "color":       0xEC4899,
        "questions": [
            ("Wie heisst du & was machst du?", "Dein Name und deine Content-Art (Clips, Edits, Stream...)", True),
            ("Deine Social Media / Plattformen", "YouTube, TikTok, Twitch, Instagram... mit Links", True),
            ("Warum moechtest du Amate Media werden?", "Beschreibe deine Motivation und was du einbringen kannst.", True),
        ],
    },
    "report": {
        "label":       "🚨 Report",
        "description": "Einen User oder Betrug melden",
        "emoji":       "🚨",
        "color":       0xE74C3C,
        "questions": [
            ("Wen moechtest du reporten?", "User-Tag oder ID des gemeldeten Users", True),
            ("Was ist passiert?", "Beschreibe den Vorfall detailliert.", True),
            ("Beweise (Screenshots/Links)", "Fuege hier Links zu Beweisen ein (optional)", False),
        ],
    },
    "bewerbung": {
        "label":       "📋 Staff Bewerbung",
        "description": "Bewirb dich als Teammitglied",
        "emoji":       "📋",
        "color":       0x3498DB,
        "questions": [
            ("Wie heisst du & wie alt bist du?", "Dein Name und dein Alter", True),
            ("Warum moechtest du Staff werden?", "Erklaere deine Motivation", True),
            ("Erfahrungen im Discord-/FiveM-Bereich?", "Bisherige Erfahrungen als Mod/Admin/Dev etc.", False),
        ],
    },
}

PRIORITY_COLORS = {"low": 0x57F287, "normal": 0x7B2FBE, "high": 0xFF9900, "urgent": 0xFF4444}
PRIORITY_LABELS = {"low": "🟢 Niedrig", "normal": "🟣 Normal", "high": "🟠 Hoch", "urgent": "🔴 Urgent"}


# ─────────────────────────────────────────────────────────────────
#  Data helpers
# ─────────────────────────────────────────────────────────────────

def load_data() -> dict:
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if not os.path.exists(DATA_FILE):
        return {"counter": 0, "active": {}}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        return {"counter": 0, "active": {}}

def save_data(data: dict):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def next_ticket_number() -> str:
    data = load_data()
    data["counter"] = data.get("counter", 0) + 1
    save_data(data)
    return f"{data['counter']:04d}"

def register_ticket(channel_id: int, user_id: int, category: str, ticket_num: str):
    data = load_data()
    data["active"][str(channel_id)] = {
        "ticket_num":   ticket_num,
        "user_id":      user_id,
        "category":     category,
        "created_at":   datetime.now(timezone.utc).isoformat(),
        "last_message": datetime.now(timezone.utc).isoformat(),
        "claimed_by":   None,
        "assigned_to":  None,
        "priority":     "normal",
        "closed":       False,
    }
    save_data(data)

def unregister_ticket(channel_id: int):
    data = load_data()
    data["active"].pop(str(channel_id), None)
    save_data(data)

def update_last_message(channel_id: int):
    data = load_data()
    key = str(channel_id)
    if key in data["active"]:
        data["active"][key]["last_message"] = datetime.now(timezone.utc).isoformat()
        save_data(data)

def get_ticket_info(channel_id: int):
    data = load_data()
    return data["active"].get(str(channel_id))

def user_has_open_ticket(user_id: int, category: str) -> bool:
    data = load_data()
    for info in data["active"].values():
        if info["user_id"] == user_id and info["category"] == category and not info.get("closed"):
            return True
    return False

def set_claimed_by(channel_id: int, claimer_id):
    data = load_data()
    key = str(channel_id)
    if key in data["active"]:
        data["active"][key]["claimed_by"] = claimer_id
        save_data(data)

def set_assigned_to(channel_id: int, assignee_id):
    data = load_data()
    key = str(channel_id)
    if key in data["active"]:
        data["active"][key]["assigned_to"] = assignee_id
        save_data(data)

def set_priority(channel_id: int, priority: str):
    data = load_data()
    key = str(channel_id)
    if key in data["active"]:
        data["active"][key]["priority"] = priority
        save_data(data)

def has_access(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    role_ids = {r.id for r in member.roles}
    return SUPPORT_ROLE_ID in role_ids or BOT_ACCESS_ROLE_ID in role_ids

def is_staff(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    role_ids = {r.id for r in member.roles}
    return SUPPORT_ROLE_ID in role_ids or BOT_ACCESS_ROLE_ID in role_ids

async def send_log(bot: commands.Bot, embed: discord.Embed, file: discord.File = None):
    if not LOG_CHANNEL_ID:
        return
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return
    ch = guild.get_channel(LOG_CHANNEL_ID)
    if ch:
        try:
            await ch.send(embed=embed, file=file) if file else await ch.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to send log embed: {e}")

def get_banner_file():
    if os.path.exists(BANNER):
        return discord.File(BANNER, filename="banner.jpg")
    return None


# ─────────────────────────────────────────────────────────────────
#  Priority Select (row 2 of PersistentControlView)
# ─────────────────────────────────────────────────────────────────

class PrioritySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="🟢 Niedrig", value="low",    description="Keine Eile"),
            discord.SelectOption(label="🟣 Normal",  value="normal", description="Standard-Prioritaet", default=True),
            discord.SelectOption(label="🟠 Hoch",    value="high",   description="Bitte zeitnah bearbeiten"),
            discord.SelectOption(label="🔴 Urgent",  value="urgent", description="Sofortige Bearbeitung noetig"),
        ]
        super().__init__(
            placeholder="🎯 Prioritaet setzen...",
            min_values=1, max_values=1,
            options=options,
            custom_id="ticket_priority_select",
            row=2,
        )

    async def callback(self, interaction: discord.Interaction):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Nur Staff kann die Prioritaet setzen.", ephemeral=True)
            return
        info = get_ticket_info(interaction.channel.id)
        if not info:
            await interaction.response.send_message("❌ Kein Ticket-Channel.", ephemeral=True)
            return
        prio  = self.values[0]
        set_priority(interaction.channel.id, prio)
        label = PRIORITY_LABELS[prio]
        color = PRIORITY_COLORS[prio]
        embed = discord.Embed(
            description=f"🎯 Prioritaet auf **{label}** gesetzt von {interaction.user.mention}.",
            color=color,
        )
        await interaction.response.send_message(embed=embed)
        log_embed = discord.Embed(title="🎯 Prioritaet geaendert", color=color)
        log_embed.add_field(name="Ticket",    value=f"`#{info['ticket_num']}`", inline=True)
        log_embed.add_field(name="Prioritaet", value=label, inline=True)
        log_embed.add_field(name="Von",        value=str(interaction.user), inline=True)
        log_embed.timestamp = discord.utils.utcnow()
        await send_log(interaction.client, log_embed)


# ─────────────────────────────────────────────────────────────────
#  Rating View
# ─────────────────────────────────────────────────────────────────

class RatingView(discord.ui.View):
    def __init__(self, ticket_num: str, opener_id: int):
        super().__init__(timeout=300)
        self.ticket_num = ticket_num
        self.opener_id  = opener_id

    async def _rate(self, interaction: discord.Interaction, stars: int):
        if interaction.user.id != self.opener_id:
            await interaction.response.send_message("❌ Nur der Ticket-Ersteller kann bewerten.", ephemeral=True)
            return
        labels = {1: "😞 Schlecht", 2: "😐 Okay", 3: "😊 Gut", 4: "😄 Super", 5: "🤩 Perfekt"}
        embed = discord.Embed(
            title="⭐ Bewertung erhalten",
            description=f"Danke fuer deine Bewertung: **{labels[stars]}** ({'⭐' * stars})\nTicket #{self.ticket_num}",
            color=0x7B2FBE,
        )
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="1⭐", style=discord.ButtonStyle.gray,    custom_id="rate_1")
    async def r1(self, i, b): await self._rate(i, 1)
    @discord.ui.button(label="2⭐", style=discord.ButtonStyle.gray,    custom_id="rate_2")
    async def r2(self, i, b): await self._rate(i, 2)
    @discord.ui.button(label="3⭐", style=discord.ButtonStyle.blurple, custom_id="rate_3")
    async def r3(self, i, b): await self._rate(i, 3)
    @discord.ui.button(label="4⭐", style=discord.ButtonStyle.blurple, custom_id="rate_4")
    async def r4(self, i, b): await self._rate(i, 4)
    @discord.ui.button(label="5⭐", style=discord.ButtonStyle.green,   custom_id="rate_5")
    async def r5(self, i, b): await self._rate(i, 5)


# ─────────────────────────────────────────────────────────────────
#  Modals
# ─────────────────────────────────────────────────────────────────

class TicketModal(discord.ui.Modal):
    def __init__(self, category_key: str, bot: commands.Bot):
        cat = CATEGORIES[category_key]
        super().__init__(title=f"Ticket: {cat['label']}")
        self.category_key = category_key
        self.bot = bot
        self.inputs = []
        for (label, placeholder, required) in cat["questions"]:
            item = discord.ui.TextInput(
                label=label,
                placeholder=placeholder,
                required=required,
                style=discord.TextStyle.paragraph if len(label) > 40 else discord.TextStyle.short,
                max_length=500,
            )
            self.add_item(item)
            self.inputs.append(item)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        guild   = interaction.guild
        member  = interaction.user
        cat     = CATEGORIES[self.category_key]
        cat_key = self.category_key

        if user_has_open_ticket(member.id, cat_key):
            await interaction.followup.send(
                f"⚠️ Du hast bereits ein offenes **{cat['label']}**-Ticket! Schliesse es zuerst.",
                ephemeral=True
            )
            return

        ticket_num   = next_ticket_number()
        channel_name = f"ticket-{ticket_num}-{member.name[:16].lower().replace(' ', '-')}"

        support_role = guild.get_role(SUPPORT_ROLE_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(
                view_channel=True, send_messages=True,
                read_message_history=True, attach_files=True, embed_links=True,
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, manage_channels=True,
                manage_messages=True, read_message_history=True, attach_files=True,
            ),
        }
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True,
                read_message_history=True, attach_files=True, manage_messages=True,
            )

        ticket_category = guild.get_channel(TICKET_CATEGORY_ID) if TICKET_CATEGORY_ID else None

        try:
            channel = await guild.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                category=ticket_category,
                topic=f"Ticket #{ticket_num} | {cat['label']} | {member} ({member.id})",
                reason=f"Ticket #{ticket_num} by {member}",
            )
        except discord.Forbidden:
            await interaction.followup.send("❌ Ich habe keine Berechtigung, Channels zu erstellen.", ephemeral=True)
            return

        register_ticket(channel.id, member.id, cat_key, ticket_num)

        answers_text = ""
        for i, inp in enumerate(self.inputs):
            if inp.value.strip():
                q_label = CATEGORIES[cat_key]["questions"][i][0]
                answers_text += f"**{q_label}**\n{inp.value.strip()}\n\n"

        embed = discord.Embed(
            title=f"{cat['emoji']} Ticket #{ticket_num} — {cat['label']}",
            description=(
                f"Hallo {member.mention}, willkommen in deinem Ticket!\n\n"
                "Unser Team wird sich so schnell wie moeglich um dein Anliegen kuemmern.\n\n"
                "─────────────────────────────────"
            ),
            color=cat["color"],
        )
        if answers_text:
            embed.add_field(name="📋 Deine Angaben", value=answers_text.strip(), inline=False)
        embed.add_field(
            name="ℹ️ Info",
            value=(
                f"👤 Geoeffnet von: {member.mention}\n"
                f"📂 Kategorie: {cat['label']}\n"
                f"🎯 Prioritaet: {PRIORITY_LABELS['normal']}\n"
                f"🕐 Erstellt: <t:{int(datetime.now(timezone.utc).timestamp())}:F>"
            ),
            inline=False,
        )
        embed.set_footer(text=f"Amate Settings  •  Ticket #{ticket_num}")
        banner_file = get_banner_file()
        if banner_file:
            embed.set_image(url="attachment://banner.jpg")

        view = PersistentControlView()
        ping_msg = member.mention
        if support_role:
            ping_msg += f" | {support_role.mention}"

        if banner_file:
            await channel.send(content=ping_msg, embed=embed, view=view, file=banner_file)
        else:
            await channel.send(content=ping_msg, embed=embed, view=view)

        confirm = discord.Embed(
            title="✅ Ticket erstellt",
            description=f"Dein Ticket wurde geoeffnet: {channel.mention}",
            color=cat["color"],
        )
        await interaction.followup.send(embed=confirm, ephemeral=True)

        log_embed = discord.Embed(title="🎫 Ticket Geoeffnet", color=cat["color"])
        log_embed.add_field(name="Ticket",    value=f"`#{ticket_num}` — {channel.mention}", inline=False)
        log_embed.add_field(name="User",      value=f"{member} (`{member.id}`)", inline=True)
        log_embed.add_field(name="Kategorie", value=cat["label"], inline=True)
        log_embed.set_thumbnail(url=member.display_avatar.url)
        log_embed.timestamp = discord.utils.utcnow()
        await send_log(self.bot, log_embed)


class CloseModal(discord.ui.Modal, title="Ticket schliessen"):
    reason = discord.ui.TextInput(
        label="Grund fuer das Schliessen",
        placeholder="z.B. Problem geloest, Keine Antwort, Spam...",
        required=False,
        max_length=300,
        style=discord.TextStyle.paragraph,
    )

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        channel = interaction.channel
        closer  = interaction.user
        reason  = self.reason.value.strip() or "Kein Grund angegeben"

        info = get_ticket_info(channel.id)
        if not info:
            await interaction.followup.send("❌ Dies ist kein Ticket-Channel.", ephemeral=True)
            return

        if TRANSCRIPT_CHANNEL_ID:
            tr_ch = interaction.guild.get_channel(TRANSCRIPT_CHANNEL_ID)
            if tr_ch:
                try:
                    transcript_file = await generate_transcript(channel)
                    cat = CATEGORIES.get(info["category"], {})
                    tr_embed = discord.Embed(
                        title=f"📋 Transcript — Ticket #{info['ticket_num']}",
                        description=f"Geschlossen von {closer.mention}\n**Grund:** {reason}",
                        color=0xFF4444,
                    )
                    tr_embed.add_field(name="Kategorie",    value=cat.get("label", info["category"]), inline=True)
                    tr_embed.add_field(name="Geoeffnet von", value=f"<@{info['user_id']}>", inline=True)
                    tr_embed.timestamp = discord.utils.utcnow()
                    await tr_ch.send(embed=tr_embed, file=transcript_file)
                except Exception as e:
                    logger.warning(f"Transcript error: {e}")

        try:
            opener = interaction.guild.get_member(info["user_id"]) or await interaction.guild.fetch_member(info["user_id"])
            if opener:
                rating_embed = discord.Embed(
                    title="⭐ Wie war der Support?",
                    description=(
                        f"Dein Ticket **#{info['ticket_num']}** wurde geschlossen.\n"
                        f"**Grund:** {reason}\n\n"
                        "Bewerte den Support mit den Buttons unten!"
                    ),
                    color=0x7B2FBE,
                )
                rating_embed.set_footer(text="Amate Settings")
                await opener.send(embed=rating_embed, view=RatingView(ticket_num=info["ticket_num"], opener_id=opener.id))
        except (discord.Forbidden, discord.HTTPException):
            pass

        close_embed = discord.Embed(
            title="🔒 Ticket wird geschlossen",
            description=f"**Geschlossen von:** {closer.mention}\n**Grund:** {reason}\n\nDieser Channel wird in 5 Sekunden geloescht.",
            color=0xFF4444,
        )
        await interaction.followup.send(embed=close_embed)

        cat = CATEGORIES.get(info["category"], {})
        log_embed = discord.Embed(title="🔒 Ticket Geschlossen", color=0xFF4444)
        log_embed.add_field(name="Ticket",          value=f"`#{info['ticket_num']}`", inline=True)
        log_embed.add_field(name="Kategorie",        value=cat.get("label", info["category"]), inline=True)
        log_embed.add_field(name="Geoeffnet von",    value=f"<@{info['user_id']}>", inline=True)
        log_embed.add_field(name="Geschlossen von",  value=f"{closer} (`{closer.id}`)", inline=True)
        log_embed.add_field(name="Grund",            value=reason, inline=False)
        log_embed.timestamp = discord.utils.utcnow()
        await send_log(self.bot, log_embed)

        unregister_ticket(channel.id)
        await asyncio.sleep(5)
        try:
            await channel.delete(reason=f"Ticket #{info['ticket_num']} closed by {closer}")
        except discord.Forbidden:
            logger.warning(f"No permission to delete ticket channel #{info['ticket_num']}")


class AddMemberModal(discord.ui.Modal, title="Member hinzufuegen"):
    user_input = discord.ui.TextInput(
        label="User ID oder @Mention",
        placeholder="z.B. 123456789012345678",
        required=True,
        max_length=100,
    )

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        raw    = self.user_input.value.strip().lstrip("<@!").rstrip(">")
        guild  = interaction.guild
        member = None
        try:
            member = guild.get_member(int(raw)) or await guild.fetch_member(int(raw))
        except Exception:
            await interaction.response.send_message("❌ User nicht gefunden.", ephemeral=True)
            return
        await interaction.channel.set_permissions(
            member, view_channel=True, send_messages=True, read_message_history=True,
        )
        embed = discord.Embed(
            description=f"✅ {member.mention} wurde zum Ticket hinzugefuegt von {interaction.user.mention}.",
            color=0x7B2FBE,
        )
        await interaction.response.send_message(embed=embed)


class RemoveMemberModal(discord.ui.Modal, title="Member entfernen"):
    user_input = discord.ui.TextInput(
        label="User ID",
        placeholder="z.B. 123456789012345678",
        required=True,
        max_length=100,
    )

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        raw    = self.user_input.value.strip().lstrip("<@!").rstrip(">")
        guild  = interaction.guild
        member = None
        try:
            member = guild.get_member(int(raw)) or await guild.fetch_member(int(raw))
        except Exception:
            await interaction.response.send_message("❌ User nicht gefunden.", ephemeral=True)
            return
        info = get_ticket_info(interaction.channel.id)
        if info and info["user_id"] == member.id:
            await interaction.response.send_message("❌ Du kannst den Ticket-Ersteller nicht entfernen.", ephemeral=True)
            return
        await interaction.channel.set_permissions(member, overwrite=None)
        embed = discord.Embed(
            description=f"✅ {member.mention} wurde aus dem Ticket entfernt von {interaction.user.mention}.",
            color=0x7B2FBE,
        )
        await interaction.response.send_message(embed=embed)


class NoteModal(discord.ui.Modal, title="Interne Notiz"):
    note = discord.ui.TextInput(
        label="Notiz (nur fuer Staff sichtbar)",
        placeholder="z.B. User hat bereits gezahlt, wartet auf Lieferung...",
        required=True,
        max_length=1000,
        style=discord.TextStyle.paragraph,
    )

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        info = get_ticket_info(interaction.channel.id)
        if not info:
            await interaction.response.send_message("❌ Kein Ticket-Channel.", ephemeral=True)
            return
        embed = discord.Embed(
            title="📝 Interne Staff-Notiz",
            description=self.note.value.strip(),
            color=0xFFCC00,
        )
        embed.set_footer(text=f"Notiz von {interaction.user.display_name}  •  Ticket #{info['ticket_num']}")
        embed.timestamp = discord.utils.utcnow()
        msg = await interaction.channel.send(embed=embed)
        try:
            await msg.pin()
        except (discord.Forbidden, discord.HTTPException):
            pass
        await interaction.response.send_message("✅ Notiz gespeichert und angepinnt.", ephemeral=True)


# ─────────────────────────────────────────────────────────────────
#  Persistent Control View  — THE ONLY view with ticket_* custom_ids
#  (removed duplicate TicketControlView that caused 40060 errors)
# ─────────────────────────────────────────────────────────────────

class PersistentControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(PrioritySelect())

    # Row 0 ───────────────────────────────────────────────────────

    @discord.ui.button(label="Schliessen", emoji="🔒", style=discord.ButtonStyle.red,
                       custom_id="ticket_close", row=0)
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        info = get_ticket_info(interaction.channel.id)
        if not info:
            await interaction.response.send_message("❌ Kein Ticket-Channel.", ephemeral=True)
            return
        if not (is_staff(interaction.user) or info["user_id"] == interaction.user.id):
            await interaction.response.send_message("❌ Keine Berechtigung.", ephemeral=True)
            return
        await interaction.response.send_modal(CloseModal(bot=interaction.client))

    @discord.ui.button(label="Claimen", emoji="👤", style=discord.ButtonStyle.blurple,
                       custom_id="ticket_claim", row=0)
    async def claim_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Nur Staff kann Tickets claimen.", ephemeral=True)
            return
        info = get_ticket_info(interaction.channel.id)
        if not info:
            await interaction.response.send_message("❌ Ticket-Daten nicht gefunden.", ephemeral=True)
            return
        if info.get("claimed_by"):
            claimer = interaction.guild.get_member(info["claimed_by"])
            await interaction.response.send_message(
                f"⚠️ Bereits geclaimed von {claimer.mention if claimer else 'jemandem'}.",
                ephemeral=True,
            )
            return
        # IMPORTANT: defer BEFORE any slow awaitable to avoid 10062
        await interaction.response.defer()
        member = interaction.user
        set_claimed_by(interaction.channel.id, member.id)
        try:
            new_name = f"claimed-{info['ticket_num']}-{member.name[:16].lower().replace(' ', '-')}"
            await interaction.channel.edit(name=new_name)
        except Exception as e:
            logger.warning(f"Could not rename channel during claim: {e}")
        embed = discord.Embed(
            description=f"👤 **{member.mention}** hat dieses Ticket geclaimed und kuemmert sich darum.",
            color=0x7B2FBE,
        )
        embed.set_footer(text=f"Ticket #{info['ticket_num']}")
        await interaction.followup.send(embed=embed)
        log_embed = discord.Embed(title="👤 Ticket Geclaimed", color=0x7B2FBE)
        log_embed.add_field(name="Ticket", value=f"`#{info['ticket_num']}`", inline=True)
        log_embed.add_field(name="Von",    value=f"{member} (`{member.id}`)", inline=True)
        log_embed.timestamp = discord.utils.utcnow()
        await send_log(interaction.client, log_embed)

    @discord.ui.button(label="Transcript", emoji="📋", style=discord.ButtonStyle.gray,
                       custom_id="ticket_transcript", row=0)
    async def transcript_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        info   = get_ticket_info(interaction.channel.id)
        if not (is_staff(member) or (info and info["user_id"] == member.id)):
            await interaction.response.send_message("❌ Keine Berechtigung.", ephemeral=True)
            return
        try:
            await interaction.response.defer(ephemeral=True, thinking=True)
        except (discord.NotFound, discord.HTTPException):
            return  # Interaction expired, silently ignore
        file = await generate_transcript(interaction.channel)
        num  = info["ticket_num"] if info else "????"
        embed = discord.Embed(
            title=f"📋 Transcript — Ticket #{num}",
            description="Hier ist das aktuelle Transcript dieses Tickets.",
            color=0x7B2FBE,
        )
        await interaction.followup.send(embed=embed, file=file, ephemeral=True)

    # Row 1 ───────────────────────────────────────────────────────

    @discord.ui.button(label="Member hinzufuegen", emoji="➕", style=discord.ButtonStyle.gray,
                       custom_id="ticket_add_member", row=1)
    async def add_member_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Nur Staff kann Member hinzufuegen.", ephemeral=True)
            return
        await interaction.response.send_modal(AddMemberModal(bot=interaction.client))

    @discord.ui.button(label="Member entfernen", emoji="➖", style=discord.ButtonStyle.gray,
                       custom_id="ticket_remove_member", row=1)
    async def remove_member_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Nur Staff kann Member entfernen.", ephemeral=True)
            return
        await interaction.response.send_modal(RemoveMemberModal(bot=interaction.client))

    @discord.ui.button(label="Notiz", emoji="📝", style=discord.ButtonStyle.gray,
                       custom_id="ticket_note", row=1)
    async def note_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Nur Staff kann Notizen hinzufuegen.", ephemeral=True)
            return
        await interaction.response.send_modal(NoteModal(bot=interaction.client))


# ─────────────────────────────────────────────────────────────────
#  Ticket Panel Select + View
# ─────────────────────────────────────────────────────────────────

class TicketSelectMenu(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=cat["label"],
                value=key,
                description=cat["description"],
                emoji=cat["emoji"],
            )
            for key, cat in CATEGORIES.items()
        ]
        super().__init__(
            placeholder="📂 Waehle eine Ticket-Kategorie...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket_select_menu",
        )

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        if selected not in CATEGORIES:
            await interaction.response.send_message("❌ Unbekannte Kategorie.", ephemeral=True)
            return
        # Use interaction.client instead of stored bot reference for persistent views
        await interaction.response.send_modal(TicketModal(category_key=selected, bot=interaction.client))


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelectMenu())


# ─────────────────────────────────────────────────────────────────
#  Cog
# ─────────────────────────────────────────────────────────────────

class TicketsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if AUTO_CLOSE_HOURS > 0:
            self.auto_close_loop.start()

    def cog_unload(self):
        if AUTO_CLOSE_HOURS > 0:
            self.auto_close_loop.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        # Register ALL persistent views on every restart
        self.bot.add_view(PersistentControlView())
        self.bot.add_view(TicketPanelView())
        logger.info("✅ Persistent views registered (PersistentControlView + TicketPanelView)")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        update_last_message(message.channel.id)

    # Auto-Close ──────────────────────────────────────────────────

    @tasks.loop(minutes=30)
    async def auto_close_loop(self):
        await self.bot.wait_until_ready()
        data   = load_data()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=AUTO_CLOSE_HOURS)

        for ch_id_str, info in list(data["active"].items()):
            if info.get("closed"):
                continue
            try:
                last = datetime.fromisoformat(info.get("last_message", info["created_at"]))
                if last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
            except Exception:
                continue

            if last < cutoff:
                guild   = self.bot.get_guild(GUILD_ID)
                channel = guild.get_channel(int(ch_id_str)) if guild else None
                if channel:
                    try:
                        embed = discord.Embed(
                            title="⏳ Auto-Close — Inaktivitaet",
                            description=(
                                f"Dieses Ticket wird automatisch geschlossen, da seit "
                                f"**{AUTO_CLOSE_HOURS} Stunden** keine Nachrichten eingegangen sind.\n\n"
                                "Wird in 10 Sekunden geloescht..."
                            ),
                            color=0xFF4444,
                        )
                        await channel.send(embed=embed)
                        log_embed = discord.Embed(title="⏳ Auto-Close (Inaktivitaet)", color=0xFF9900)
                        log_embed.add_field(name="Ticket",      value=f"`#{info['ticket_num']}`", inline=True)
                        log_embed.add_field(name="Inaktiv seit", value=f"{AUTO_CLOSE_HOURS}h",    inline=True)
                        log_embed.timestamp = discord.utils.utcnow()
                        await send_log(self.bot, log_embed)
                        if TRANSCRIPT_CHANNEL_ID:
                            tr_ch = guild.get_channel(TRANSCRIPT_CHANNEL_ID)
                            if tr_ch:
                                file = await generate_transcript(channel)
                                tr_embed = discord.Embed(
                                    title=f"📋 Auto-Transcript — Ticket #{info['ticket_num']}",
                                    description="Geschlossen wegen Inaktivitaet.",
                                    color=0xFF9900,
                                )
                                await tr_ch.send(embed=tr_embed, file=file)
                        unregister_ticket(int(ch_id_str))
                        await asyncio.sleep(10)
                        await channel.delete(reason="Auto-closed: inactivity")
                    except Exception as e:
                        logger.error(f"Auto-close error for channel {ch_id_str}: {e}\n{traceback.format_exc()}")

    # Slash Commands ──────────────────────────────────────────────

    @app_commands.command(name="sendtickets", description="Sendet das Ticket-Panel in diesen Channel.")
    async def sendtickets(self, interaction: discord.Interaction):
        if not has_access(interaction.user):
            await interaction.response.send_message("❌ Du hast keine Berechtigung.", ephemeral=True)
            return
        # FIX: defer FIRST before sending banner (avoids 40060)
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title="🎫 Amate Settings — Support",
            description=(
                "## Brauchst du Hilfe oder moechtest etwas kaufen?\n\n"
                "Waehle unten die passende **Ticket-Kategorie** aus und "
                "unser Team wird sich so schnell wie moeglich bei dir melden.\n\n"
                "─────────────────────────────────\n"
                "🔧 **Support** — Allgemeine Hilfe & Fragen\n"
                "🛒 **Script Kaufen** — FiveM Scripts anfragen\n"
                "🪪 **Ident** — Branding & Identity\n"
                "🎨 **Design** — Grafik & UI Design\n"
                "📷 **Werde Amate Media** — Media Creator werden\n"
                "🚨 **Report** — User oder Betrug melden\n"
                "📋 **Staff Bewerbung** — Werde Teil des Teams\n"
                "─────────────────────────────────\n\n"
                "> ⚠️ **Hinweis:** Bitte oeffne nur ein Ticket pro Anliegen.\n"
                "> Spam oder Missbrauch fuehrt zu einem Ban."
            ),
            color=0x7B2FBE,
        )
        file = get_banner_file()
        if file:
            embed.set_image(url="attachment://banner.jpg")
        embed.set_footer(
            text="Amate Settings  •  Waehle eine Kategorie um ein Ticket zu oeffnen",
            icon_url=interaction.guild.icon.url if interaction.guild and interaction.guild.icon else None,
        )
        view = TicketPanelView()
        if file:
            await interaction.channel.send(file=file, embed=embed, view=view)
        else:
            await interaction.channel.send(embed=embed, view=view)
        await interaction.followup.send("✅ Ticket-Panel gesendet!", ephemeral=True)

    @app_commands.command(name="closeticket", description="Schliesst das aktuelle Ticket.")
    async def closeticket(self, interaction: discord.Interaction):
        if not has_access(interaction.user):
            await interaction.response.send_message("❌ Du hast keine Berechtigung.", ephemeral=True)
            return
        if not get_ticket_info(interaction.channel.id):
            await interaction.response.send_message("❌ Dies ist kein Ticket-Channel.", ephemeral=True)
            return
        await interaction.response.send_modal(CloseModal(bot=self.bot))

    @app_commands.command(name="addmember", description="Fuegt einen Member zum Ticket hinzu.")
    @app_commands.describe(member="Der Member, der hinzugefuegt werden soll")
    async def addmember(self, interaction: discord.Interaction, member: discord.Member):
        if not has_access(interaction.user):
            await interaction.response.send_message("❌ Du hast keine Berechtigung.", ephemeral=True)
            return
        if not get_ticket_info(interaction.channel.id):
            await interaction.response.send_message("❌ Dies ist kein Ticket-Channel.", ephemeral=True)
            return
        await interaction.channel.set_permissions(
            member, view_channel=True, send_messages=True, read_message_history=True,
        )
        embed = discord.Embed(
            description=f"✅ {member.mention} wurde von {interaction.user.mention} hinzugefuegt.",
            color=0x7B2FBE,
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="removemember", description="Entfernt einen Member aus dem Ticket.")
    @app_commands.describe(member="Der Member, der entfernt werden soll")
    async def removemember(self, interaction: discord.Interaction, member: discord.Member):
        if not has_access(interaction.user):
            await interaction.response.send_message("❌ Du hast keine Berechtigung.", ephemeral=True)
            return
        info = get_ticket_info(interaction.channel.id)
        if not info:
            await interaction.response.send_message("❌ Dies ist kein Ticket-Channel.", ephemeral=True)
            return
        if info["user_id"] == member.id:
            await interaction.response.send_message("❌ Du kannst den Ticket-Ersteller nicht entfernen.", ephemeral=True)
            return
        await interaction.channel.set_permissions(member, overwrite=None)
        embed = discord.Embed(
            description=f"✅ {member.mention} wurde von {interaction.user.mention} entfernt.",
            color=0x7B2FBE,
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ticketstats", description="Zeigt Ticket-Statistiken.")
    async def ticketstats(self, interaction: discord.Interaction):
        if not has_access(interaction.user):
            await interaction.response.send_message("❌ Du hast keine Berechtigung.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        data   = load_data()
        active = [v for v in data["active"].values() if not v.get("closed")]
        cats_count: dict[str, int] = {}
        for v in active:
            cats_count[v["category"]] = cats_count.get(v["category"], 0) + 1
        embed = discord.Embed(title="📊 Ticket Statistiken", color=0x7B2FBE)
        embed.add_field(name="Gesamt erstellt", value=f"`{data['counter']}`", inline=True)
        embed.add_field(name="Aktuell offen",   value=f"`{len(active)}`",    inline=True)
        embed.add_field(name="\u200b",           value="\u200b",             inline=True)
        for key, cat in CATEGORIES.items():
            count = cats_count.get(key, 0)
            embed.add_field(name=cat["label"], value=f"`{count}` offen", inline=True)
        embed.timestamp = discord.utils.utcnow()
        file = get_banner_file()
        if file:
            embed.set_thumbnail(url="attachment://banner.jpg")
            await interaction.followup.send(embed=embed, file=file, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="listtickets", description="Listet alle offenen Tickets auf.")
    async def listtickets(self, interaction: discord.Interaction):
        if not has_access(interaction.user):
            await interaction.response.send_message("❌ Du hast keine Berechtigung.", ephemeral=True)
            return
        data   = load_data()
        active = {k: v for k, v in data["active"].items() if not v.get("closed")}
        if not active:
            await interaction.response.send_message("✅ Keine offenen Tickets.", ephemeral=True)
            return
        embed = discord.Embed(title=f"🎫 Offene Tickets ({len(active)})", color=0x7B2FBE)
        for ch_id, info in list(active.items())[:25]:
            cat   = CATEGORIES.get(info["category"], {})
            ch    = interaction.guild.get_channel(int(ch_id))
            prio  = PRIORITY_LABELS.get(info.get("priority", "normal"), "🟣 Normal")
            claimed = f"<@{info['claimed_by']}>" if info.get("claimed_by") else "Niemand"
            ts    = int(datetime.fromisoformat(info["created_at"]).timestamp())
            embed.add_field(
                name=f"#{info['ticket_num']} — {cat.get('label', info['category'])}",
                value=(
                    f"👤 <@{info['user_id']}>\n"
                    f"🎯 {prio}\n"
                    f"🔧 Geclaimed: {claimed}\n"
                    f"📌 {ch.mention if ch else f'`{ch_id}`'}\n"
                    f"🕐 <t:{ts}:R>"
                ),
                inline=True,
            )
        embed.set_footer(text="Amate Settings  •  /listtickets")
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="assignticket", description="Weist das Ticket einem Staff-Member zu.")
    @app_commands.describe(member="Staff-Member dem das Ticket zugewiesen werden soll")
    async def assignticket(self, interaction: discord.Interaction, member: discord.Member):
        if not has_access(interaction.user):
            await interaction.response.send_message("❌ Du hast keine Berechtigung.", ephemeral=True)
            return
        info = get_ticket_info(interaction.channel.id)
        if not info:
            await interaction.response.send_message("❌ Dies ist kein Ticket-Channel.", ephemeral=True)
            return
        set_assigned_to(interaction.channel.id, member.id)
        await interaction.channel.set_permissions(
            member, view_channel=True, send_messages=True, read_message_history=True,
        )
        embed = discord.Embed(
            description=f"📌 Ticket **#{info['ticket_num']}** wurde {member.mention} zugewiesen von {interaction.user.mention}.",
            color=0x7B2FBE,
        )
        await interaction.response.send_message(embed=embed)
        try:
            notify = discord.Embed(
                title="📌 Dir wurde ein Ticket zugewiesen",
                description=f"Ticket **#{info['ticket_num']}** wartet auf dich: {interaction.channel.mention}",
                color=0x7B2FBE,
            )
            await member.send(embed=notify)
        except (discord.Forbidden, discord.HTTPException):
            pass

    @app_commands.command(name="renameticket", description="Benennt den aktuellen Ticket-Channel um.")
    @app_commands.describe(name="Neuer Channel-Name")
    async def renameticket(self, interaction: discord.Interaction, name: str):
        if not has_access(interaction.user):
            await interaction.response.send_message("❌ Du hast keine Berechtigung.", ephemeral=True)
            return
        if not get_ticket_info(interaction.channel.id):
            await interaction.response.send_message("❌ Dies ist kein Ticket-Channel.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        try:
            await interaction.channel.edit(name=name)
            await interaction.followup.send(f"✅ Channel umbenannt zu `{name}`.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ Keine Berechtigung zum Umbenennen.", ephemeral=True)

    @app_commands.command(name="ticketinfo", description="Zeigt Infos zum aktuellen Ticket.")
    async def ticketinfo(self, interaction: discord.Interaction):
        if not has_access(interaction.user):
            await interaction.response.send_message("❌ Du hast keine Berechtigung.", ephemeral=True)
            return
        info = get_ticket_info(interaction.channel.id)
        if not info:
            await interaction.response.send_message("❌ Dies ist kein Ticket-Channel.", ephemeral=True)
            return
        cat        = CATEGORIES.get(info["category"], {})
        claimed    = f"<@{info['claimed_by']}>" if info.get("claimed_by") else "Niemand"
        assigned   = f"<@{info['assigned_to']}>" if info.get("assigned_to") else "Niemand"
        prio       = PRIORITY_LABELS.get(info.get("priority", "normal"), "🟣 Normal")
        created_ts = int(datetime.fromisoformat(info["created_at"]).timestamp())
        embed = discord.Embed(title=f"🎫 Ticket #{info['ticket_num']} Info", color=cat.get("color", 0x7B2FBE))
        embed.add_field(name="Kategorie",     value=cat.get("label", info["category"]), inline=True)
        embed.add_field(name="Geoeffnet von", value=f"<@{info['user_id']}>",           inline=True)
        embed.add_field(name="Prioritaet",    value=prio,                               inline=True)
        embed.add_field(name="Geclaimed von", value=claimed,                            inline=True)
        embed.add_field(name="Zugewiesen an", value=assigned,                           inline=True)
        embed.add_field(name="Erstellt",      value=f"<t:{created_ts}:F>",             inline=False)
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="setnote", description="Fuegt eine interne Staff-Notiz zum Ticket hinzu.")
    @app_commands.describe(text="Die Notiz")
    async def setnote(self, interaction: discord.Interaction, text: str):
        if not has_access(interaction.user):
            await interaction.response.send_message("❌ Du hast keine Berechtigung.", ephemeral=True)
            return
        info = get_ticket_info(interaction.channel.id)
        if not info:
            await interaction.response.send_message("❌ Dies ist kein Ticket-Channel.", ephemeral=True)
            return
        embed = discord.Embed(
            title="📝 Interne Staff-Notiz",
            description=text,
            color=0xFFCC00,
        )
        embed.set_footer(text=f"Notiz von {interaction.user.display_name}  •  Ticket #{info['ticket_num']}")
        embed.timestamp = discord.utils.utcnow()
        msg = await interaction.channel.send(embed=embed)
        try:
            await msg.pin()
        except (discord.Forbidden, discord.HTTPException):
            pass
        await interaction.response.send_message("✅ Notiz gespeichert und angepinnt.", ephemeral=True)

    @app_commands.command(name="setpriority", description="Setzt die Prioritaet des aktuellen Tickets.")
    @app_commands.describe(priority="Prioritaet: low, normal, high, urgent")
    @app_commands.choices(priority=[
        app_commands.Choice(name="🟢 Niedrig", value="low"),
        app_commands.Choice(name="🟣 Normal",  value="normal"),
        app_commands.Choice(name="🟠 Hoch",    value="high"),
        app_commands.Choice(name="🔴 Urgent",  value="urgent"),
    ])
    async def setpriority(self, interaction: discord.Interaction, priority: str):
        if not has_access(interaction.user):
            await interaction.response.send_message("❌ Du hast keine Berechtigung.", ephemeral=True)
            return
        info = get_ticket_info(interaction.channel.id)
        if not info:
            await interaction.response.send_message("❌ Dies ist kein Ticket-Channel.", ephemeral=True)
            return
        set_priority(interaction.channel.id, priority)
        label = PRIORITY_LABELS[priority]
        color = PRIORITY_COLORS[priority]
        embed = discord.Embed(
            description=f"🎯 Prioritaet auf **{label}** gesetzt von {interaction.user.mention}.",
            color=color,
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(TicketsCog(bot))
