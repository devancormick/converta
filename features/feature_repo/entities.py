from feast import Entity, ValueType

applicant = Entity(
    name="applicant",
    value_type=ValueType.STRING,
    description="Unique applicant identifier",
)
