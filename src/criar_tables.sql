create table logs_alertas (
    id int auto_increment primary key,
    ip_receptor varchar(255) not null,
    hostname_chamador varchar(255) not null,
    nome_usuario varchar(255) not null,
    nome_sala varchar(255) not null,
    data_hora datetime not null,
    status varchar(255) not null
);

create table usuarios (
    id int auto_increment primary key,
    nome_usuario varchar(255) not null,
    USERNAME varchar(255) not null
);

create table salas (
    id int auto_increment primary key,
    nome_sala varchar(255) not null,
    hostname varchar(255) not null,
    setor varchar(255) not null
);

create table receptores (
    id int auto_increment primary key,
    ip_receptor varchar(255) not null,
    nome_receptor varchar(255) not null
);


