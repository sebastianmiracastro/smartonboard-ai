"""Reestablece la base de datos desde CERO y vuelve a aplicar el seed.

Borra TODAS las tablas conocidas por los modelos, las recrea vacías, aplica
las migraciones ligeras y siembra los datos mínimos (empresa + Directora RR.HH.).

Solo backend / línea de comandos — NO está expuesto en el frontend a propósito.

Uso:
    cd backend
    venv\\Scripts\\activate
    python -m app.db.reset

Para saltar la confirmación (útil en scripts):
    python -m app.db.reset --yes
"""
import sys

from app.db.database import engine
from app.models import models
from app.db.migrate import run_migrations
from app.db.seed import seed


def reset(confirm: bool = True):
    if confirm:
        print("Esto BORRARÁ todos los datos de la base de datos:")
        print(f"  {engine.url}")
        answer = input("¿Continuar? Escribe 'si' para confirmar: ").strip().lower()
        if answer not in ("si", "sí", "s", "yes", "y"):
            print("Cancelado. No se hizo ningún cambio.")
            return

    print("Borrando tablas...")
    models.Base.metadata.drop_all(bind=engine)

    print("Recreando tablas...")
    models.Base.metadata.create_all(bind=engine)
    run_migrations()

    print("Aplicando seed...")
    seed()

    print("Base de datos reestablecida desde cero.")


if __name__ == "__main__":
    skip_confirm = "--yes" in sys.argv or "-y" in sys.argv
    reset(confirm=not skip_confirm)
