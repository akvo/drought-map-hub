CREATE USER akvo WITH PASSWORD 'password';

CREATE DATABASE drought_map_hub
WITH OWNER = akvo
     template = template0
     ENCODING = 'UTF-8'
     LC_COLLATE = 'en_US.UTF-8'
     LC_CTYPE = 'en_US.UTF-8';

\c drought_map_hub

CREATE EXTENSION IF NOT EXISTS ltree WITH SCHEMA public;

-- Fix CI: permission denied to create a database
ALTER USER akvo CREATEDB;