from datetime import timedelta

from feast import Feature, FeatureView, FileSource, ValueType

from features.feature_repo.entities import applicant

behavioral_source = FileSource(
    path="data/features/behavioral",
    timestamp_field="event_timestamp",
)

text_source = FileSource(
    path="data/features/text",
    timestamp_field="event_timestamp",
)

contextual_source = FileSource(
    path="data/features/contextual",
    timestamp_field="event_timestamp",
)

historical_source = FileSource(
    path="data/features/historical",
    timestamp_field="event_timestamp",
)

behavioral_features = FeatureView(
    name="applicant_behavioral",
    entities=[applicant],
    ttl=timedelta(days=7),
    features=[
        Feature(name="time_on_page_seconds", dtype=ValueType.FLOAT),
        Feature(name="click_count", dtype=ValueType.INT64),
        Feature(name="return_visits", dtype=ValueType.INT64),
        Feature(name="session_count", dtype=ValueType.INT64),
        Feature(name="device_type", dtype=ValueType.STRING),
    ],
    source=behavioral_source,
    online=True,
)

text_features = FeatureView(
    name="message_text",
    entities=[applicant],
    ttl=timedelta(days=1),
    features=[
        Feature(name="message_length", dtype=ValueType.INT64),
        Feature(name="readability_score", dtype=ValueType.FLOAT),
        Feature(name="sentiment_score", dtype=ValueType.FLOAT),
        Feature(name="urgency_keyword_count", dtype=ValueType.INT64),
        Feature(name="embedding_dim0", dtype=ValueType.FLOAT),
    ],
    source=text_source,
    online=True,
)

contextual_features = FeatureView(
    name="contextual",
    entities=[applicant],
    ttl=timedelta(hours=1),
    features=[
        Feature(name="channel", dtype=ValueType.STRING),
        Feature(name="hour_of_day", dtype=ValueType.INT64),
        Feature(name="day_of_week", dtype=ValueType.INT64),
        Feature(name="campaign_id", dtype=ValueType.STRING),
    ],
    source=contextual_source,
    online=True,
)

historical_features = FeatureView(
    name="applicant_historical",
    entities=[applicant],
    ttl=timedelta(days=30),
    features=[
        Feature(name="past_application_count", dtype=ValueType.INT64),
        Feature(name="prior_engagement_rate", dtype=ValueType.FLOAT),
        Feature(name="loan_segment", dtype=ValueType.STRING),
        Feature(name="days_since_last_application", dtype=ValueType.INT64),
    ],
    source=historical_source,
    online=True,
)
