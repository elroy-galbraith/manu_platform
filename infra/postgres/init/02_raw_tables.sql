CREATE TABLE raw.member (
    member_id       text PRIMARY KEY,
    company         text NOT NULL,
    sector          text NOT NULL,
    parish          text,
    lat             numeric,
    lon             numeric,
    employees       integer,
    size_band       text,
    lead_time_days  integer,
    export_status   text,
    export_markets  text
);

CREATE TABLE raw.product (
    member_id     text NOT NULL REFERENCES raw.member (member_id),
    product_name  text NOT NULL,
    PRIMARY KEY (member_id, product_name)
);

CREATE TABLE raw.capacity_submission (
    member_id        text NOT NULL REFERENCES raw.member (member_id),
    quarter          text NOT NULL,
    capacity         integer NOT NULL,
    unit             text NOT NULL,
    utilization_pct  integer NOT NULL,
    PRIMARY KEY (member_id, quarter)
);

CREATE TABLE raw.certification (
    member_id            text NOT NULL REFERENCES raw.member (member_id),
    cert_type            text NOT NULL,
    verification_status  text NOT NULL DEFAULT 'unverified',
    PRIMARY KEY (member_id, cert_type)
);

CREATE TABLE raw.energy_submission (
    member_id                 text NOT NULL REFERENCES raw.member (member_id),
    quarter                   text NOT NULL,
    monthly_kwh               integer NOT NULL,
    generator_share_pct       integer NOT NULL,
    monthly_energy_cost_jmd   bigint NOT NULL,
    energy_pct_of_prod_cost   numeric NOT NULL,
    renewable_adoption        text,
    PRIMARY KEY (member_id, quarter)
);

CREATE TABLE raw.readiness_assessment (
    member_id              text NOT NULL REFERENCES raw.member (member_id),
    quarter                text NOT NULL,
    score_packaging        integer NOT NULL,
    score_logistics        integer NOT NULL,
    score_quality_systems  integer NOT NULL,
    score_export_history   integer NOT NULL,
    PRIMARY KEY (member_id, quarter)
);

CREATE TABLE raw.buyer_request (
    request_id          text PRIMARY KEY,
    buyer               text NOT NULL,
    buyer_type          text,
    location            text,
    products_needed     text,
    sector              text,
    required_cert       text,
    monthly_volume      integer,
    volume_unit         text,
    max_lead_time_days  integer
);

CREATE TABLE raw.visibility_setting (
    member_id    text NOT NULL REFERENCES raw.member (member_id),
    field_group  text NOT NULL,
    tier         integer NOT NULL CHECK (tier BETWEEN 1 AND 3),
    changed_at   timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (member_id, field_group)
);

CREATE TABLE raw.workforce_submission (
    member_id    text NOT NULL REFERENCES raw.member (member_id),
    quarter      text NOT NULL,
    employment   integer,
    vacancies    integer,
    skills_gaps  text,
    PRIMARY KEY (member_id, quarter)
);
