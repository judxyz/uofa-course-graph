-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.


CREATE TABLE public.courses (
  id integer GENERATED ALWAYS AS IDENTITY NOT NULL,
  code character varying NOT NULL UNIQUE,
  subject character varying NOT NULL,
  number character varying NOT NULL,
  title text NOT NULL,
  description text,
  raw_prereq_text text,
  raw_coreq_text text,
  catalog_url text,
  parse_status character varying NOT NULL DEFAULT 'unparsed'::character varying,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT courses_pkey PRIMARY KEY (id)
);

CREATE TABLE public.requirement_groups (
  id integer GENERATED ALWAYS AS IDENTITY NOT NULL,
  course_id integer NOT NULL,
  group_type character varying NOT NULL, -- ANY_OF, COREQ, PREREQ
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  parent_group_id integer,
  visual_style text,
  CONSTRAINT requirement_groups_pkey PRIMARY KEY (id),
  CONSTRAINT requirement_groups_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id)
);

CREATE TABLE public.requirement_items (
  id integer GENERATED ALWAYS AS IDENTITY NOT NULL,
  group_id integer NOT NULL,
  required_course_id integer,
  relation_type character varying NOT NULL DEFAULT 'prereq'::character varying,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  item_order integer,
  missing_course_code text,
  requirement_text text,
  CONSTRAINT requirement_items_pkey PRIMARY KEY (id),
  CONSTRAINT requirement_items_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.requirement_groups(id),
  CONSTRAINT requirement_items_required_course_id_fkey FOREIGN KEY (required_course_id) REFERENCES public.courses(id)
);
CREATE TABLE public.course_edges (
  id integer GENERATED ALWAYS AS IDENTITY NOT NULL,
  source_course_id integer NOT NULL,
  target_course_id integer NOT NULL,
  edge_type character varying NOT NULL,
  group_id integer,
  label text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT course_edges_pkey PRIMARY KEY (id),
  CONSTRAINT course_edges_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.requirement_groups(id),
  CONSTRAINT course_edges_source_course_id_fkey FOREIGN KEY (source_course_id) REFERENCES public.courses(id),
  CONSTRAINT course_edges_target_course_id_fkey FOREIGN KEY (target_course_id) REFERENCES public.courses(id)
);
