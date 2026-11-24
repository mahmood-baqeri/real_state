import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_usersession_auth_method_usersession_device_type_and_more"),
    ]
    operations = [
        migrations.CreateModel(
            name="WebSocketTicket",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("ticket_jti", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("session_jti", models.CharField(db_index=True, max_length=64)),
                ("agency_id", models.UUIDField(blank=True, db_index=True, null=True)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="websocket_tickets", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "accounts_websocket_ticket"},
        ),
        migrations.AddIndex(
            model_name="websocketticket",
            index=models.Index(fields=["user", "expires_at"], name="accounts_ws_user_exp_idx"),
        ),
        migrations.AddIndex(
            model_name="websocketticket",
            index=models.Index(fields=["ticket_jti", "used_at"], name="accounts_ws_jti_used_idx"),
        ),
    ]
