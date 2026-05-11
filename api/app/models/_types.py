from sqlalchemy import JSON, BigInteger, Integer, Uuid
from sqlalchemy.dialects.postgresql import JSONB

JSONType = JSONB().with_variant(JSON(), "sqlite")
UUIDType = Uuid(as_uuid=True, native_uuid=True)
BigIntPk = BigInteger().with_variant(Integer(), "sqlite")
