from rest_framework.permissions import AllowAny
from rest_framework.schemas import get_schema_view


schema_view = get_schema_view(
    title="MNLV API",
    description="Schéma OpenAPI (généré par DRF).",
    version="1.0.0",
    permission_classes=[AllowAny],
)

