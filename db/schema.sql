CREATE TABLE sites (
    site_id BIGSERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    location VARCHAR(100) NOT NULL 
);

CREATE TABLE assets (
    asset_id BIGSERIAL PRIMARY KEY,
    site_id  BIGINT NOT NULL REFERENCES sites(site_id),
    asset_name   VARCHAR(50)  NOT NULL,
    asset_type   VARCHAR(50)  NOT NULL,

    status  VARCHAR(20)  NOT NULL DEFAULT 'healthy'
        CHECK (
            status IN (
                'healthy',
                'degraded',
                'unhealthy',
                'maintenance'
            )
        ),

    created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE(site_id, asset_name)
);


CREATE TABLE metrics (
    metric_id BIGSERIAL PRIMARY KEY,
    asset_id  BIGINT    NOT NULL REFERENCES assets(asset_id),
    metric_type VARCHAR(50) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE incidents (
    incident_id BIGSERIAL PRIMARY KEY,
    asset_id BIGINT  NOT NULL REFERENCES assets(asset_id),
    incident_type VARCHAR(50) NOT NULL,
    severity  VARCHAR(10) NOT NULL 
        CHECK (
            severity IN (
                'low',
                'medium',
                'high',
                'critical'
            )
        ),
    status  VARCHAR(20) NOT NULL DEFAULT 'open'
        CHECK (
            status IN (
                'open',
                'investigating',
                'resolved',
                'closed'
            )
        ),
    message TEXT,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ 
);
