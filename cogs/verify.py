import discord
from discord.ext import commands
from discord import app_commands
import os, logging, traceback

log = logging.getLogger("amate.verify")

GUILD_ID        = int(os.getenv("GUILD_ID", "0"))
VERIFIED_ROLE_ID = int(os.getenv("VERIFIED_ROLE_ID", "0"))
LOG_CHANNEL_ID  = int(os.getenv("LOG_CHANNEL_ID", "0"))

# ─────────────────────────────────────────────
#  Persistent Verify Button
# ─────────────────────────────────────────────
class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="✅  Verify",
        style=discord.ButtonStyle.blurple,
        custom_id="wake_verify_button"
    )
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild  = interaction.guild
        member = interaction.user

        verified_role = guild.get_role(VERIFIED_ROLE_ID)
        if not verified_role:
            await interaction.response.send_message("❌ Verified role not configured. Contact an admin.", ephemeral=True)
            return

        if verified_role in member.roles:
            await interaction.response.send_message("⚡ Du bist bereits verifiziert!", ephemeral=True)
            return

        try:
            await member.add_roles(verified_role, reason="Self-verified via button")
        except discord.Forbidden:
            log.warning(f"No permission to assign verified role to {member} ({member.id})")
            await interaction.response.send_message("❌ Keine Berechtigung, Rollen zuzuweisen.", ephemeral=True)
            return

        embed = discord.Embed(
            title="⚡ Verification Successful",
            description=(
                f"Willkommen auf **Amate**, {member.mention}!\n\n"
                "Du hast nun vollen Zugriff auf den Server.\n"
                "Viel Spaß — schau dir die Channels an. 🔥"
            ),
            color=0x7B2FBE
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.set_footer(text="Amate • FiveM Scripts & Commissions")
        await interaction.response.send_message(embed=embed, ephemeral=True)

        if LOG_CHANNEL_ID:
            log_ch = guild.get_channel(LOG_CHANNEL_ID)
            if log_ch:
                log = discord.Embed(title="🔐 Member Verified", color=0x7B2FBE)
                log.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
                log.add_field(name="Role", value=verified_role.mention, inline=True)
                log.set_thumbnail(url=member.display_avatar.url)
                log.timestamp = discord.utils.utcnow()
                await log_ch.send(embed=log)


# ─────────────────────────────────────────────
#  Cog
# ─────────────────────────────────────────────
class VerifyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(VerifyView())

    # ── /sendverify ──────────────────────────
    @app_commands.command(name="sendverify", description="Sendet das Verify-Embed in diesen Channel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def sendverify(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🔒 Amate — Verifizierung",
            description=(
                "## 👋 Willkommen auf **Amate**\n\n"
                "Um **vollen Zugang** zum Server zu erhalten, musst du dich einmalig verifizieren.\n\n"
                "**Klicke einfach auf den Button unten** — du erhältst sofort die "
                "**Verified**-Rolle und Zugriff auf alle Channels.\n\n"
                "─────────────────────────────\n"
                "🔒 **Warum verifizieren?**\n"
                "Um unsere Community vor Bots und Raidern zu schützen.\n\n"
                "⚡ **FiveM Scripts & Commissions**\n"
                "Die besten Settings & Scripts für deinen FiveM Server.\n"
                "─────────────────────────────"
            ),
            color=0x7B2FBE
        )
        banner_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "banner.jpg")
        file = None
        if os.path.exists(banner_path):
            file = discord.File(banner_path, filename="banner.jpg")
            embed.set_image(url="attachment://banner.jpg")
        embed.set_footer(
            text="Amate  •  Klicke auf Verify um Zugang zu erhalten",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )
        view = VerifyView()
        if file:
            await interaction.channel.send(file=file, embed=embed, view=view)
        else:
            await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ Verify-Embed gesendet!", ephemeral=True)

    # ── /unverify ────────────────────────────
    @app_commands.command(name="unverify", description="Entfernt die Verified-Rolle von einem Member.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(member="Der Member, der entverifiziert werden soll")
    async def unverify(self, interaction: discord.Interaction, member: discord.Member):
        role = interaction.guild.get_role(VERIFIED_ROLE_ID)
        if not role:
            await interaction.response.send_message("❌ Verified-Rolle nicht gefunden.", ephemeral=True)
            return
        if role not in member.roles:
            await interaction.response.send_message(f"⚠️ {member.mention} ist nicht verifiziert.", ephemeral=True)
            return
        await member.remove_roles(role, reason=f"Unverified by {interaction.user}")
        await interaction.response.send_message(f"✅ Verified-Rolle von {member.mention} entfernt.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(VerifyCog(bot))
