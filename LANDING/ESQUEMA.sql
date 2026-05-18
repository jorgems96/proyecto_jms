--este fichero se encarga de crear la base de datos y los esquemas


------------------------------------------------BASE DE DATOS DEL PROYECTO
CREATE DATABASE IF NOT EXISTS PROYECTO;

-------------------------------------------------------------CAPA LANDING
CREATE SCHEMA IF NOT EXISTS PROYECTO.LANDING;

-----------------------------------------------------------------CAPA RAW
CREATE SCHEMA IF NOT EXISTS PROYECTO.RAW;

-------------------------------------------------------------CAPA CLEANSED
CREATE SCHEMA IF NOT EXISTS PROYECTO.CLEANSED;


-----------------------------------------------------------CAPA CONFORMED
CREATE SCHEMA IF NOT EXISTS PROYECTO.CONFORMED;


------------------------------------------------------CAPA OPTIMIZED
CREATE SCHEMA IF NOT EXISTS PROYECTO.OPTIMIZED;
