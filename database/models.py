from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class PoolTokenLink(SQLModel, table=True):
    pool_id: Optional[str] = Field(
        default=None,
        foreign_key="pool.id",
        primary_key=True,
    )
    token_id: Optional[str] = Field(
        default=None, foreign_key="token.id", primary_key=True
    )


class Pool(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    protocol: str

    tokens: list["Token"] = Relationship(
        back_populates="pools",
        link_model=PoolTokenLink,
    )
    snapshots: list["PoolSnapshot"] = Relationship(
        back_populates="pool",
    )


class PoolSnapshot(SQLModel, table=True):
    id: str = Field(primary_key=True)
    blockNumber: int
    timestamp: int
    totalValueLocked: float
    cumulativeReward: float

    pool_id: str = Field(default=None, foreign_key="pool.id")
    pool: Pool = Relationship(
        back_populates="snapshots",
        sa_relationship_kwargs={"cascade": "all, delete"},
    )


class Token(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    symbol: str

    pools: list["Pool"] = Relationship(
        back_populates="tokens",
        link_model=PoolTokenLink,
    )
    snapshots: list["TokenSnapshot"] = Relationship(
        back_populates="token",
    )


class TokenSnapshot(SQLModel, table=True):
    id: str = Field(primary_key=True)
    blockNumber: int
    timestamp: int
    price: Optional[float]

    token_id: str = Field(default=None, foreign_key="token.id")
    token: Token = Relationship(
        back_populates="snapshots",
        sa_relationship_kwargs={"cascade": "all, delete"},
    )
