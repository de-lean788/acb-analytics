"""
tests/test_validators.py

Tests críticos que deben pasar SIEMPRE antes de cualquier push.
Cubren los dos bugs principales del proyecto:
  1. Jugadores rivales mezclados en análisis de Bilbao
  2. Stats acumulativas sumadas en lugar de MAX()
"""
import pytest
import pandas as pd
from pathlib import Path

from analytics.validators import (
    is_bilbao_home,
    get_bilbao_flag,
    validate_schema,
    validate_bilbao_players,
    validate_substitution_pairs,
    validate_stats_not_duplicated,
    BILBAO_ROSTER_NAMES,
    REQUIRED_COLUMNS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_csv_home():
    """Partido donde Bilbao es LOCAL."""
    return "20251026_104492_SurneBilbaoBasket_vs_MoraBancAndorra_plays.csv"

@pytest.fixture
def sample_csv_away():
    """Partido donde Bilbao es VISITANTE."""
    return "20251019_104481_JoventutBadalona_vs_SurneBilbaoBasket_plays.csv"

@pytest.fixture
def bilbao_players():
    return ["Margiris Normantas", "Darrun Hilliard", "Luke Petrasek", "Tryggvi Hlinason"]

@pytest.fixture
def rival_players():
    """Jugadores que NO son de Bilbao — nunca deben aparecer en análisis."""
    return ["Ricky Rubio", "Adam Hanga", "Sam Dekker", "Guillem Vives"]

@pytest.fixture
def df_with_bilbao_flag(bilbao_players, rival_players):
    """DataFrame con is_bilbao correctamente asignado."""
    rows = (
        [{"player_name": p, "is_bilbao": True,  "pts": 10, "play_type": 0} for p in bilbao_players] +
        [{"player_name": p, "is_bilbao": False, "pts": 8,  "play_type": 0} for p in rival_players]
    )
    return pd.DataFrame(rows)

@pytest.fixture
def df_contaminated(bilbao_players, rival_players):
    """DataFrame con jugadores rivales marcados como Bilbao — el bug."""
    all_players = bilbao_players + rival_players
    rows = [{"player_name": p, "is_bilbao": True, "pts": 10, "play_type": 0} for p in all_players]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 1. Tests de inferencia home/away desde nombre de fichero
# ---------------------------------------------------------------------------
class TestIsBilbaoHome:
    def test_bilbao_es_local(self, sample_csv_home):
        assert is_bilbao_home(sample_csv_home) is True

    def test_bilbao_es_visitante(self, sample_csv_away):
        assert is_bilbao_home(sample_csv_away) is False

    def test_formato_invalido_lanza_error(self):
        with pytest.raises(ValueError, match="Nombre de fichero no reconocido"):
            is_bilbao_home("partido_sin_formato_correcto.csv")

    def test_acepta_path_object(self, sample_csv_home):
        assert is_bilbao_home(Path(sample_csv_home)) is True

    @pytest.mark.parametrize("filename,expected", [
        ("20251109_104511_SurneBilbaoBasket_vs_CasademontZaragoza_plays.csv", True),
        ("20251101_104495_BAXIManresa_vs_SurneBilbaoBasket_plays.csv", False),
        ("20251026_104492_SurneBilbaoBasket_vs_MoraBancAndorra_plays.csv", True),
        ("20251019_104481_JoventutBadalona_vs_SurneBilbaoBasket_plays.csv", False),
    ])
    def test_todos_los_partidos_conocidos(self, filename, expected):
        assert is_bilbao_home(filename) == expected


# ---------------------------------------------------------------------------
# 2. Tests de aislamiento de jugadores — EL BUG PRINCIPAL
# ---------------------------------------------------------------------------
class TestBilbaoPlayerIsolation:
    def test_jugadores_limpios_pasan_validacion(self, df_with_bilbao_flag):
        """Con datos correctos, no debe lanzar excepción."""
        validate_bilbao_players(df_with_bilbao_flag, strict=False)  # no crash

    def test_jugadores_rivales_detectados_strict(self, df_contaminated):
        """Si hay rivales marcados como Bilbao, strict=True debe lanzar excepción."""
        with pytest.raises(ValueError, match="JUGADORES NO RECONOCIDOS EN ROSTER BILBAO"):
            validate_bilbao_players(df_contaminated, strict=True)

    def test_jugadores_rivales_detectados_warning(self, df_contaminated, caplog):
        """Con strict=False, debe loggear WARNING sin lanzar excepción."""
        import logging
        with caplog.at_level(logging.WARNING):
            validate_bilbao_players(df_contaminated, strict=False)
        assert "JUGADORES NO RECONOCIDOS" in caplog.text

    def test_ningún_rival_en_roster_oficial(self, rival_players):
        """Los jugadores rivales conocidos NO deben estar en el roster de Bilbao."""
        for player in rival_players:
            assert player not in BILBAO_ROSTER_NAMES, (
                f"'{player}' está en el roster de Bilbao pero no debería. "
                "Verifica BILBAO_ROSTER_NAMES en analytics/validators.py"
            )

    def test_bilbao_flag_home_filtra_correctamente(self, sample_csv_home):
        """
        Bug crítico: cuando Bilbao es LOCAL, is_bilbao_flag debe ser True.
        df[df['is_local'] == flag] debe devolver solo jugadores de Bilbao.
        """
        flag = get_bilbao_flag(sample_csv_home)
        assert flag is True, "Cuando Bilbao es local, el flag debe ser True"

    def test_bilbao_flag_away_filtra_correctamente(self, sample_csv_away):
        """
        Bug crítico: cuando Bilbao es VISITANTE, is_bilbao_flag debe ser False.
        Si usamos True aquí, filtramos al rival en lugar de a Bilbao.
        """
        flag = get_bilbao_flag(sample_csv_away)
        assert flag is False, (
            "Cuando Bilbao es visitante, el flag debe ser False. "
            "Usar is_local==True hardcodeado es el bug que mezcla jugadores rivales."
        )


# ---------------------------------------------------------------------------
# 3. Tests de stats acumulativas — MAX() vs SUM()
# ---------------------------------------------------------------------------
class TestAccumulativeStats:
    def test_max_correcto(self):
        """MAX() sobre stats acumulativas da el valor real del partido."""
        # Simulación: el CSV tiene 3 filas para el mismo jugador (acumulativo)
        df = pd.DataFrame([
            {"match_id": 1, "player_name": "Normantas", "pts": 5},
            {"match_id": 1, "player_name": "Normantas", "pts": 12},
            {"match_id": 1, "player_name": "Normantas", "pts": 18},  # valor real final
        ])
        result = df.groupby(["match_id", "player_name"])["pts"].max().iloc[0]
        assert result == 18

    def test_sum_incorrecto(self):
        """SUM() sobre stats acumulativas duplica/triplica los valores."""
        df = pd.DataFrame([
            {"match_id": 1, "player_name": "Normantas", "pts": 5},
            {"match_id": 1, "player_name": "Normantas", "pts": 12},
            {"match_id": 1, "player_name": "Normantas", "pts": 18},
        ])
        wrong_result = df.groupby(["match_id", "player_name"])["pts"].sum().iloc[0]
        assert wrong_result == 35, "SUM() da 35, pero el valor real es 18"

    def test_validate_stats_pasa_con_datos_correctos(self):
        """Con MAX() aplicado, la validación no debe lanzar excepción."""
        df = pd.DataFrame([
            {"player_name": "Normantas", "pts": 18},
            {"player_name": "Hilliard",  "pts": 22},
        ])
        validate_stats_not_duplicated(df)  # no crash

    def test_validate_stats_detecta_duplicacion(self):
        """Si alguien suma stats acumulativas, un jugador puede superar 65 pts."""
        df = pd.DataFrame([
            {"player_name": "Normantas", "pts": 80},  # imposible → SUM() aplicado
        ])
        with pytest.raises(ValueError, match="POSIBLE DUPLICACIÓN DE STATS"):
            validate_stats_not_duplicated(df)


# ---------------------------------------------------------------------------
# 4. Tests de pares de sustituciones
# ---------------------------------------------------------------------------
class TestSubstitutionPairs:
    def _make_sub_df(self, quarter, minute, second, team, entries, exits):
        rows = []
        for _ in range(entries):
            rows.append({
                "match_id": 1, "quarter": quarter, "minute": minute,
                "second": second, "team_role": team, "play_type": 115,
                "player_name": f"player_in_{_}",
            })
        for _ in range(exits):
            rows.append({
                "match_id": 1, "quarter": quarter, "minute": minute,
                "second": second, "team_role": team, "play_type": 112,
                "player_name": f"player_out_{_}",
            })
        return pd.DataFrame(rows)

    def test_pares_balanceados_no_genera_warning(self, caplog):
        import logging
        df = self._make_sub_df(1, 5, 30, "away", entries=2, exits=2)
        with caplog.at_level(logging.WARNING):
            validate_substitution_pairs(df)
        assert "desbalanceada" not in caplog.text

    def test_pares_desbalanceados_genera_warning(self, caplog):
        import logging
        df = self._make_sub_df(1, 5, 30, "away", entries=3, exits=2)
        with caplog.at_level(logging.WARNING):
            validate_substitution_pairs(df)
        assert "desbalanceada" in caplog.text


# ---------------------------------------------------------------------------
# 5. Tests de schema
# ---------------------------------------------------------------------------
class TestSchema:
    def test_schema_completo_pasa(self):
        df = pd.DataFrame(columns=REQUIRED_COLUMNS)
        validate_schema(df)  # no crash

    def test_schema_con_columnas_faltantes_lanza_error(self):
        df = pd.DataFrame(columns=["match_id", "quarter"])  # faltan muchas
        with pytest.raises(ValueError, match="Columnas faltantes"):
            validate_schema(df)
