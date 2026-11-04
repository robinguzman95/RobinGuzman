"""Tablas de la base de datos (ver Plan Técnico, "Esquema de base de datos")."""

from datetime import date, datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class GameRow(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(50))
    main_count: Mapped[int] = mapped_column(Integer)
    main_max: Mapped[int] = mapped_column(Integer)
    extra_max: Mapped[int | None] = mapped_column(Integer)
    # Colores separados por coma, en el orden oficial; nulo si el juego no usa colores.
    color_set: Mapped[str | None] = mapped_column(String(100))

    draws: Mapped[list["Draw"]] = relationship(back_populates="game")


class Draw(Base):
    __tablename__ = "draws"
    __table_args__ = (
        UniqueConstraint("game_id", "draw_number", name="uq_draws_game_number"),
        Index("ix_draws_game_date", "game_id", "draw_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"))
    draw_number: Mapped[int] = mapped_column(Integer)
    draw_date: Mapped[date] = mapped_column(Date)
    jackpot_cop: Mapped[int | None] = mapped_column(BigInteger)
    source_url: Mapped[str | None] = mapped_column(String(300))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    game: Mapped[GameRow] = relationship(back_populates="draws")
    balls: Mapped[list["DrawBall"]] = relationship(
        back_populates="draw", cascade="all, delete-orphan", order_by="DrawBall.position"
    )


class DrawBall(Base):
    __tablename__ = "draw_balls"
    __table_args__ = (Index("ix_draw_balls_draw_id", "draw_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    draw_id: Mapped[int] = mapped_column(ForeignKey("draws.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer)
    number: Mapped[int] = mapped_column(Integer)
    color: Mapped[str | None] = mapped_column(String(20))
    is_extra: Mapped[bool] = mapped_column(Boolean, default=False)

    draw: Mapped[Draw] = relationship(back_populates="balls")


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"))
    strategy: Mapped[str] = mapped_column(String(40))
    params_json: Mapped[str] = mapped_column(Text, default="{}")
    window_draws: Mapped[int] = mapped_column(Integer)
    date_from: Mapped[date] = mapped_column(Date)
    date_to: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    results: Mapped[list["BacktestResult"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id", ondelete="CASCADE"))
    avg_hits: Mapped[float] = mapped_column(Float)
    hit_distribution_json: Mapped[str] = mapped_column(Text)
    baseline_mean: Mapped[float] = mapped_column(Float)
    baseline_p5: Mapped[float] = mapped_column(Float)
    baseline_p95: Mapped[float] = mapped_column(Float)
    p_value: Mapped[float] = mapped_column(Float)

    run: Mapped[BacktestRun] = relationship(back_populates="results")
