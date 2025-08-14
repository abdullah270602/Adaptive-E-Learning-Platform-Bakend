create table if not exists users
(
    id          uuid                     default uuid_generate_v4() not null
        primary key,
    email       text                                                not null
        unique,
    name        text,
    profile_pic text,
    created_at  timestamp with time zone default CURRENT_TIMESTAMP,
    updated_at  timestamp with time zone default CURRENT_TIMESTAMP
);

alter table users
    owner to adaptive_learning_db_owner;

create table if not exists books
(
    id         uuid not null
        primary key,
    user_id    uuid
        references users
            on delete cascade,
    title      text not null,
    file_name  text not null,
    file_id    text not null
        unique,
    s3_key     text not null,
    created_at timestamp default now()
);

alter table books
    owner to adaptive_learning_db_owner;

create table if not exists chapters
(
    id             uuid not null
        primary key,
    book_id        uuid
        references books
            on delete cascade,
    chapter_number text not null,
    title          text not null,
    created_at     timestamp default now()
);

alter table chapters
    owner to adaptive_learning_db_owner;

create table if not exists sections
(
    id           uuid not null
        primary key,
    chapter_id   uuid
        references chapters
            on delete cascade,
    title        text not null,
    page         integer,
    s3_key       text,
    embedding_id text,
    added_date   timestamp default now()
);

alter table sections
    owner to adaptive_learning_db_owner;

create table if not exists learning_profiles
(
    id                uuid      default gen_random_uuid() not null
        primary key,
    user_id           uuid
        references users
            on delete cascade,
    visual_score      numeric(3, 2),
    reading_score     numeric(3, 2),
    kinesthetic_score numeric(3, 2),
    primary_style     text,
    description       text,
    created_at        timestamp default now()
);

alter table learning_profiles
    owner to adaptive_learning_db_owner;

create table if not exists presentations
(
    id                uuid      default gen_random_uuid() not null
        primary key,
    user_id           uuid
        references users
            on delete cascade,
    title             text                                not null,
    original_filename text                                not null,
    s3_key            text                                not null,
    total_slides      integer,
    has_speaker_notes boolean   default false,
    created_at        timestamp default now()
);

alter table presentations
    owner to adaptive_learning_db_owner;

create table if not exists models
(
    id           uuid                     default gen_random_uuid() not null
        primary key,
    display_name text                                               not null,
    model_name   text                                               not null,
    service      text                                               not null,
    is_active    boolean                  default true,
    created_at   timestamp with time zone default CURRENT_TIMESTAMP,
    updated_at   timestamp with time zone default CURRENT_TIMESTAMP
);

alter table models
    owner to adaptive_learning_db_owner;

create table if not exists chat_sessions
(
    id            uuid                     default gen_random_uuid() not null
        primary key,
    user_id       uuid                                               not null
        references users
            on delete cascade,
    document_id   uuid                                               not null,
    document_type text                                               not null,
    created_at    timestamp with time zone default CURRENT_TIMESTAMP,
    updated_at    timestamp with time zone default CURRENT_TIMESTAMP,
    unique (user_id, document_id, document_type)
);

alter table chat_sessions
    owner to adaptive_learning_db_owner;

create table if not exists document_progress
(
    id            uuid                     default gen_random_uuid() not null
        primary key,
    user_id       uuid                                               not null
        references users
            on delete cascade,
    document_id   uuid                                               not null,
    document_type text                                               not null,
    page_number   integer,
    section_id    uuid,
    updated_at    timestamp with time zone default CURRENT_TIMESTAMP,
    chapter_id    uuid,
    unique (user_id, document_id, document_type),
    constraint unique_user_doc
        unique (user_id, document_id)
);

alter table document_progress
    owner to adaptive_learning_db_owner;

create table if not exists user_streaks
(
    user_id          uuid                not null
        primary key,
    current_streak   integer   default 0 not null,
    longest_streak   integer   default 0 not null,
    last_active_date date                not null,
    updated_at       timestamp default now()
);

alter table user_streaks
    owner to adaptive_learning_db_owner;

create table if not exists tool_responses
(
    id            uuid                     default gen_random_uuid() not null
        primary key,
    tool_type     text                                               not null,
    response      jsonb,
    created_at    timestamp with time zone default CURRENT_TIMESTAMP,
    response_text text
);

alter table tool_responses
    owner to adaptive_learning_db_owner;

create table if not exists chat_messages
(
    id               uuid                     default gen_random_uuid() not null
        primary key,
    chat_session_id  uuid                                               not null
        references chat_sessions
            on delete cascade,
    role             text                                               not null
        constraint chat_messages_role_check
            check (role = ANY (ARRAY ['user'::text, 'assistant'::text])),
    content          text                                               not null,
    model_id         uuid
        references models,
    tool_response_id uuid
        references tool_responses,
    tool_type        text,
    created_at       timestamp with time zone default CURRENT_TIMESTAMP
);

alter table chat_messages
    owner to adaptive_learning_db_owner;

create table if not exists notes
(
    id         uuid                     default gen_random_uuid() not null
        primary key,
    user_id    uuid
        references users
            on delete cascade,
    title      text                                               not null,
    filename   text                                               not null,
    s3_key     text                                               not null,
    created_at timestamp with time zone default now()             not null,
    updated_at timestamp with time zone default now()             not null
);

alter table notes
    owner to adaptive_learning_db_owner;

create table if not exists user_quizzes
(
    id         uuid      default gen_random_uuid() not null
        primary key,
    user_id    uuid                                not null
        constraint fk_user_quizzes_user_id
            references users
            on delete cascade,
    doc_id     uuid,
    num_mcqs   integer,
    mcq_data   json                                not null,
    created_at timestamp default CURRENT_TIMESTAMP,
    updated_at timestamp default CURRENT_TIMESTAMP
);

alter table user_quizzes
    owner to adaptive_learning_db_owner;

create table if not exists quiz_history
(
    id         uuid default gen_random_uuid() not null
        primary key,
    quiz_data  json                           not null,
    quiz_id    uuid                           not null,
    doc_id     uuid                           not null,
    doc_name   varchar(255)                   not null,
    score      varchar(10)                    not null,
    accuracy   numeric(5, 2)                  not null,
    user_id    uuid                           not null
        constraint fk_quiz_history_user_id
            references users
            on delete cascade,
    time_taken integer
);

alter table quiz_history
    owner to adaptive_learning_db_owner;

create or replace function uuid_nil() returns uuid
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function uuid_nil() owner to cloud_admin;

create or replace function uuid_ns_dns() returns uuid
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function uuid_ns_dns() owner to cloud_admin;

create or replace function uuid_ns_url() returns uuid
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function uuid_ns_url() owner to cloud_admin;

create or replace function uuid_ns_oid() returns uuid
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function uuid_ns_oid() owner to cloud_admin;

create or replace function uuid_ns_x500() returns uuid
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function uuid_ns_x500() owner to cloud_admin;

create or replace function uuid_generate_v1() returns uuid
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function uuid_generate_v1() owner to cloud_admin;

create or replace function uuid_generate_v1mc() returns uuid
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function uuid_generate_v1mc() owner to cloud_admin;

create or replace function uuid_generate_v3(namespace uuid, name text) returns uuid
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function uuid_generate_v3(uuid, text) owner to cloud_admin;

create or replace function uuid_generate_v4() returns uuid
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function uuid_generate_v4() owner to cloud_admin;

create or replace function uuid_generate_v5(namespace uuid, name text) returns uuid
    immutable
    strict
    parallel safe
    language c
as
$$
begin
-- missing source code
end;
$$;

alter function uuid_generate_v5(uuid, text) owner to cloud_admin;

create or replace function update_timestamp() returns trigger
    language plpgsql
as
$$
BEGIN
   NEW.updated_at = CURRENT_TIMESTAMP;
   RETURN NEW;
END;
$$;

alter function update_timestamp() owner to adaptive_learning_db_owner;

create trigger set_updated_at
    before update
    on users
    for each row
execute procedure update_timestamp();

create trigger update_models_timestamp
    before update
    on models
    for each row
execute procedure update_timestamp();

create or replace function cleanup_orphaned_tool_responses() returns trigger
    language plpgsql
as
$$
BEGIN
    -- When a chat_message is deleted, check if its tool_response becomes orphaned
    IF OLD.tool_response_id IS NOT NULL THEN
        -- Delete the tool_response if no other chat_messages reference it
        DELETE FROM tool_responses 
        WHERE id = OLD.tool_response_id
        AND NOT EXISTS (
            SELECT 1 FROM chat_messages 
            WHERE tool_response_id = OLD.tool_response_id
        );
    END IF;
    
    RETURN OLD;
END;
$$;

alter function cleanup_orphaned_tool_responses() owner to adaptive_learning_db_owner;

create trigger cleanup_tool_responses_trigger
    after delete
    on chat_messages
    for each row
execute procedure cleanup_orphaned_tool_responses();

