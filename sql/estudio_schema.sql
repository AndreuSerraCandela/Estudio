-- Esquema de expedientes del estudio (SQL Server)
-- Base de datos: Estudio (misma instancia que Objetos)

IF OBJECT_ID('dbo.expedientes', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.expedientes (
        id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        numero_expediente NVARCHAR(50) NOT NULL,
        cliente NVARCHAR(255) NOT NULL,
        trabajo NVARCHAR(MAX) NULL,
        comercial NVARCHAR(255) NULL,
        ot NVARCHAR(100) NULL,
        proyecto NVARCHAR(255) NULL,
        fecha_inicio DATE NULL,
        fecha_finalizacion DATE NULL,
        producto NVARCHAR(255) NULL,
        acabado NVARCHAR(255) NULL,
        observaciones NVARCHAR(MAX) NULL,
        disenador NVARCHAR(255) NULL,
        bc_cliente_id NVARCHAR(100) NULL,
        bc_comercial_id NVARCHAR(100) NULL,
        bc_proyecto_id NVARCHAR(100) NULL,
        created_at DATETIME2 NOT NULL CONSTRAINT DF_expedientes_created DEFAULT SYSUTCDATETIME(),
        updated_at DATETIME2 NOT NULL CONSTRAINT DF_expedientes_updated DEFAULT SYSUTCDATETIME(),
        CONSTRAINT UQ_expedientes_numero UNIQUE (numero_expediente)
    );
END;

IF OBJECT_ID('dbo.documentos', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.documentos (
        id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        expediente_id INT NOT NULL,
        strapi_id INT NOT NULL,
        strapi_document_id NVARCHAR(100) NULL,
        url NVARCHAR(1024) NOT NULL,
        nombre NVARCHAR(512) NOT NULL,
        tipo NVARCHAR(50) NOT NULL CONSTRAINT DF_documentos_tipo DEFAULT 'otro',
        tipo_origen NVARCHAR(50) NULL,
        descripcion NVARCHAR(MAX) NULL,
        mime_type NVARCHAR(128) NULL,
        created_at DATETIME2 NOT NULL CONSTRAINT DF_documentos_created DEFAULT SYSUTCDATETIME(),
        CONSTRAINT FK_documentos_expediente FOREIGN KEY (expediente_id)
            REFERENCES dbo.expedientes(id) ON DELETE CASCADE
    );
END;

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'idx_documentos_expediente' AND object_id = OBJECT_ID('dbo.documentos')
)
    CREATE INDEX idx_documentos_expediente ON dbo.documentos(expediente_id);

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'idx_expedientes_numero' AND object_id = OBJECT_ID('dbo.expedientes')
)
    CREATE INDEX idx_expedientes_numero ON dbo.expedientes(numero_expediente);

IF OBJECT_ID('dbo.correos', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.correos (
        id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        expediente_id INT NOT NULL,
        direccion NVARCHAR(20) NOT NULL,
        asunto NVARCHAR(500) NULL,
        destinatario NVARCHAR(500) NULL,
        remitente NVARCHAR(500) NULL,
        fecha DATETIME2 NULL,
        conversation_id NVARCHAR(255) NULL,
        outlook_entry_id NVARCHAR(500) NULL,
        internet_message_id NVARCHAR(500) NULL,
        documento_id INT NULL,
        created_at DATETIME2 NOT NULL CONSTRAINT DF_correos_created DEFAULT SYSUTCDATETIME(),
        CONSTRAINT FK_correos_expediente FOREIGN KEY (expediente_id)
            REFERENCES dbo.expedientes(id) ON DELETE CASCADE,
        CONSTRAINT FK_correos_documento FOREIGN KEY (documento_id)
            REFERENCES dbo.documentos(id)
    );
END;

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'idx_correos_expediente' AND object_id = OBJECT_ID('dbo.correos')
)
    CREATE INDEX idx_correos_expediente ON dbo.correos(expediente_id);

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'idx_correos_internet_message' AND object_id = OBJECT_ID('dbo.correos')
)
    CREATE INDEX idx_correos_internet_message ON dbo.correos(internet_message_id);

IF OBJECT_ID('dbo.usuario_config', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.usuario_config (
        id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        presencia_user_id INT NOT NULL,
        metodo_correo NVARCHAR(30) NOT NULL CONSTRAINT DF_usuario_config_metodo DEFAULT 'cliente_correo',
        updated_at DATETIME2 NOT NULL CONSTRAINT DF_usuario_config_updated DEFAULT SYSUTCDATETIME(),
        CONSTRAINT UQ_usuario_config_presencia UNIQUE (presencia_user_id)
    );
END;

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'idx_usuario_config_presencia' AND object_id = OBJECT_ID('dbo.usuario_config')
)
    CREATE INDEX idx_usuario_config_presencia ON dbo.usuario_config(presencia_user_id);

IF COL_LENGTH('dbo.usuario_config', 'imap_host') IS NULL
    ALTER TABLE dbo.usuario_config ADD imap_host NVARCHAR(255) NULL;
IF COL_LENGTH('dbo.usuario_config', 'imap_port') IS NULL
    ALTER TABLE dbo.usuario_config ADD imap_port INT NOT NULL CONSTRAINT DF_usuario_config_imap_port DEFAULT 993;
IF COL_LENGTH('dbo.usuario_config', 'imap_use_ssl') IS NULL
    ALTER TABLE dbo.usuario_config ADD imap_use_ssl BIT NOT NULL CONSTRAINT DF_usuario_config_imap_ssl DEFAULT 1;
IF COL_LENGTH('dbo.usuario_config', 'imap_username') IS NULL
    ALTER TABLE dbo.usuario_config ADD imap_username NVARCHAR(255) NULL;
IF COL_LENGTH('dbo.usuario_config', 'imap_password_enc') IS NULL
    ALTER TABLE dbo.usuario_config ADD imap_password_enc NVARCHAR(MAX) NULL;
IF COL_LENGTH('dbo.usuario_config', 'imap_carpeta_entrada') IS NULL
    ALTER TABLE dbo.usuario_config ADD imap_carpeta_entrada NVARCHAR(255) NOT NULL CONSTRAINT DF_usuario_config_imap_inbox DEFAULT 'INBOX';
IF COL_LENGTH('dbo.usuario_config', 'imap_carpeta_enviados') IS NULL
    ALTER TABLE dbo.usuario_config ADD imap_carpeta_enviados NVARCHAR(255) NOT NULL CONSTRAINT DF_usuario_config_imap_sent DEFAULT 'Sent Items';
IF COL_LENGTH('dbo.usuario_config', 'imap_guardar_copia_enviados') IS NULL
    ALTER TABLE dbo.usuario_config ADD imap_guardar_copia_enviados BIT NOT NULL CONSTRAINT DF_usuario_config_imap_copy_sent DEFAULT 0;
IF COL_LENGTH('dbo.usuario_config', 'smtp_host') IS NULL
    ALTER TABLE dbo.usuario_config ADD smtp_host NVARCHAR(255) NULL;
IF COL_LENGTH('dbo.usuario_config', 'smtp_port') IS NULL
    ALTER TABLE dbo.usuario_config ADD smtp_port INT NULL;
IF COL_LENGTH('dbo.usuario_config', 'smtp_use_tls') IS NULL
    ALTER TABLE dbo.usuario_config ADD smtp_use_tls BIT NOT NULL CONSTRAINT DF_usuario_config_smtp_tls DEFAULT 1;
IF COL_LENGTH('dbo.usuario_config', 'smtp_use_ssl') IS NULL
    ALTER TABLE dbo.usuario_config ADD smtp_use_ssl BIT NOT NULL CONSTRAINT DF_usuario_config_smtp_ssl DEFAULT 0;

IF OBJECT_ID('dbo.peticiones', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.peticiones (
        id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        tipo NVARCHAR(20) NOT NULL,
        empresa NVARCHAR(150) NOT NULL,
        referencia NVARCHAR(50) NOT NULL,
        titulo NVARCHAR(255) NOT NULL,
        cliente NVARCHAR(255) NULL,
        bc_cliente_id NVARCHAR(100) NULL,
        comercial NVARCHAR(255) NOT NULL,
        bc_comercial_id NVARCHAR(50) NULL,
        fecha DATE NOT NULL,
        descripcion NVARCHAR(MAX) NULL,
        expediente_id INT NULL,
        imagen_nueva BIT NOT NULL CONSTRAINT DF_peticiones_imagen_nueva DEFAULT 0,
        presencia_user_id INT NOT NULL,
        estado NVARCHAR(20) NOT NULL CONSTRAINT DF_peticiones_estado DEFAULT 'pendiente',
        created_at DATETIME2 NOT NULL CONSTRAINT DF_peticiones_created DEFAULT SYSUTCDATETIME(),
        CONSTRAINT FK_peticiones_expediente FOREIGN KEY (expediente_id)
            REFERENCES dbo.expedientes(id) ON DELETE SET NULL
    );
END;

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'idx_peticiones_referencia' AND object_id = OBJECT_ID('dbo.peticiones')
)
    CREATE INDEX idx_peticiones_referencia ON dbo.peticiones(tipo, referencia);

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'idx_peticiones_usuario' AND object_id = OBJECT_ID('dbo.peticiones')
)
    CREATE INDEX idx_peticiones_usuario ON dbo.peticiones(presencia_user_id, created_at);

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'idx_peticiones_expediente' AND object_id = OBJECT_ID('dbo.peticiones')
)
    CREATE INDEX idx_peticiones_expediente ON dbo.peticiones(expediente_id);

IF OBJECT_ID('dbo.peticion_adjuntos', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.peticion_adjuntos (
        id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        peticion_id INT NOT NULL,
        nombre NVARCHAR(512) NOT NULL,
        url NVARCHAR(1024) NOT NULL,
        mime_type NVARCHAR(128) NULL,
        created_at DATETIME2 NOT NULL CONSTRAINT DF_peticion_adjuntos_created DEFAULT SYSUTCDATETIME(),
        CONSTRAINT FK_peticion_adjuntos_peticion FOREIGN KEY (peticion_id)
            REFERENCES dbo.peticiones(id) ON DELETE CASCADE
    );
END;

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'idx_peticion_adjuntos_peticion' AND object_id = OBJECT_ID('dbo.peticion_adjuntos')
)
    CREATE INDEX idx_peticion_adjuntos_peticion ON dbo.peticion_adjuntos(peticion_id);

IF OBJECT_ID('dbo.estudio_config', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.estudio_config (
        id INT NOT NULL PRIMARY KEY,
        ot_automatica BIT NOT NULL CONSTRAINT DF_estudio_config_ot_automatica DEFAULT 0
    );
END;

IF COL_LENGTH('dbo.estudio_config', 'ot_automatica') IS NULL
    ALTER TABLE dbo.estudio_config ADD ot_automatica BIT NOT NULL CONSTRAINT DF_estudio_config_ot_automatica DEFAULT 0;

IF OBJECT_ID('dbo.estudio_config', 'U') IS NOT NULL
    EXEC('IF NOT EXISTS (SELECT 1 FROM dbo.estudio_config WHERE id = 1) INSERT INTO dbo.estudio_config (id, ot_automatica) VALUES (1, 0)');

IF COL_LENGTH('dbo.expedientes', 'bc_empresa') IS NULL
    ALTER TABLE dbo.expedientes ADD bc_empresa NVARCHAR(150) NULL;
IF COL_LENGTH('dbo.expedientes', 'medios_bc_user') IS NULL
    ALTER TABLE dbo.expedientes ADD medios_bc_user NVARCHAR(150) NULL;
IF COL_LENGTH('dbo.expedientes', 'medios_empleado') IS NULL
    ALTER TABLE dbo.expedientes ADD medios_empleado NVARCHAR(50) NULL;
IF COL_LENGTH('dbo.expedientes', 'medios_nombre') IS NULL
    ALTER TABLE dbo.expedientes ADD medios_nombre NVARCHAR(255) NULL;
IF COL_LENGTH('dbo.expedientes', 'medios_email') IS NULL
    ALTER TABLE dbo.expedientes ADD medios_email NVARCHAR(255) NULL;

IF COL_LENGTH('dbo.documentos', 'aprobacion') IS NULL
    ALTER TABLE dbo.documentos ADD aprobacion NVARCHAR(30) NOT NULL CONSTRAINT DF_documentos_aprobacion DEFAULT 'no_requiere';
IF COL_LENGTH('dbo.documentos', 'tipo_origen') IS NULL
    ALTER TABLE dbo.documentos ADD tipo_origen NVARCHAR(50) NULL;
IF COL_LENGTH('dbo.documentos', 'medios_bc_user') IS NULL
    ALTER TABLE dbo.documentos ADD medios_bc_user NVARCHAR(150) NULL;
IF COL_LENGTH('dbo.documentos', 'medios_empleado') IS NULL
    ALTER TABLE dbo.documentos ADD medios_empleado NVARCHAR(50) NULL;
IF COL_LENGTH('dbo.documentos', 'medios_nombre') IS NULL
    ALTER TABLE dbo.documentos ADD medios_nombre NVARCHAR(255) NULL;
IF COL_LENGTH('dbo.documentos', 'medios_email') IS NULL
    ALTER TABLE dbo.documentos ADD medios_email NVARCHAR(255) NULL;

IF OBJECT_ID('dbo.arte_finales', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.arte_finales (
        id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        expediente_id INT NOT NULL,
        descripcion NVARCHAR(500) NOT NULL,
        aprobacion NVARCHAR(30) NOT NULL CONSTRAINT DF_arte_finales_aprobacion DEFAULT 'no_requiere',
        medios_bc_user NVARCHAR(150) NULL,
        medios_empleado NVARCHAR(50) NULL,
        medios_nombre NVARCHAR(255) NULL,
        medios_email NVARCHAR(255) NULL,
        validado BIT NOT NULL CONSTRAINT DF_arte_finales_validado DEFAULT 0,
        validado_en DATETIME2 NULL,
        validado_por INT NULL,
        validado_por_nombre NVARCHAR(255) NULL,
        created_at DATETIME2 NOT NULL CONSTRAINT DF_arte_finales_created DEFAULT SYSUTCDATETIME(),
        CONSTRAINT FK_arte_finales_expediente FOREIGN KEY (expediente_id)
            REFERENCES dbo.expedientes(id) ON DELETE CASCADE
    );
END;

IF OBJECT_ID('dbo.arte_final_documentos', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.arte_final_documentos (
        arte_final_id INT NOT NULL,
        documento_id INT NOT NULL,
        CONSTRAINT PK_arte_final_documentos PRIMARY KEY (arte_final_id, documento_id),
        CONSTRAINT FK_arte_final_documentos_arte FOREIGN KEY (arte_final_id)
            REFERENCES dbo.arte_finales(id) ON DELETE CASCADE,
        CONSTRAINT FK_arte_final_documentos_documento FOREIGN KEY (documento_id)
            REFERENCES dbo.documentos(id)
    );
END;

IF OBJECT_ID('dbo.arte_finales', 'U') IS NOT NULL
   AND OBJECT_ID('dbo.arte_final_documentos', 'U') IS NOT NULL
   AND COL_LENGTH('dbo.documentos', 'aprobacion') IS NOT NULL
EXEC(N'
DECLARE @id INT, @expediente INT, @descripcion NVARCHAR(500), @aprobacion NVARCHAR(30),
        @bc NVARCHAR(150), @empleado NVARCHAR(50), @nombre NVARCHAR(255), @email NVARCHAR(255),
        @validado BIT, @validado_en DATETIME2, @validado_por INT, @validado_nombre NVARCHAR(255),
        @origen NVARCHAR(50), @nuevo INT;
DECLARE antiguos CURSOR LOCAL FAST_FORWARD FOR
    SELECT id, expediente_id, LEFT(COALESCE(NULLIF(descripcion, N''''), nombre), 500),
           ISNULL(aprobacion, N''no_requiere''), medios_bc_user, medios_empleado, medios_nombre, medios_email,
           ISNULL(validado, 0), validado_en, validado_por, validado_por_nombre, tipo_origen
    FROM dbo.documentos
    WHERE tipo = N''arte_final''
      AND NOT EXISTS (SELECT 1 FROM dbo.arte_final_documentos j WHERE j.documento_id = documentos.id);
OPEN antiguos;
FETCH NEXT FROM antiguos INTO @id, @expediente, @descripcion, @aprobacion, @bc, @empleado, @nombre, @email, @validado, @validado_en, @validado_por, @validado_nombre, @origen;
WHILE @@FETCH_STATUS = 0
BEGIN
    INSERT INTO dbo.arte_finales (
        expediente_id, descripcion, aprobacion, medios_bc_user, medios_empleado, medios_nombre, medios_email,
        validado, validado_en, validado_por, validado_por_nombre
    ) VALUES (
        @expediente, @descripcion, @aprobacion, @bc, @empleado, @nombre, @email,
        @validado, @validado_en, @validado_por, @validado_nombre
    );
    SET @nuevo = SCOPE_IDENTITY();
    INSERT INTO dbo.arte_final_documentos (arte_final_id, documento_id) VALUES (@nuevo, @id);
    UPDATE dbo.documentos
       SET tipo = COALESCE(NULLIF(@origen, N''''), N''otro''), tipo_origen = NULL
     WHERE id = @id;
    FETCH NEXT FROM antiguos INTO @id, @expediente, @descripcion, @aprobacion, @bc, @empleado, @nombre, @email, @validado, @validado_en, @validado_por, @validado_nombre, @origen;
END
CLOSE antiguos;
DEALLOCATE antiguos;
');

IF OBJECT_ID('dbo.arte_final_envios', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.arte_final_envios (
        id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        arte_final_id INT NOT NULL,
        destinatario NVARCHAR(500) NOT NULL,
        asunto NVARCHAR(500) NULL,
        mensaje NVARCHAR(MAX) NULL,
        fecha DATETIME2 NOT NULL CONSTRAINT DF_arte_final_envios_fecha DEFAULT SYSUTCDATETIME(),
        enviado_por_nombre NVARCHAR(255) NULL,
        correo_id INT NULL,
        zip_documento_id INT NULL,
        CONSTRAINT FK_arte_final_envios_arte FOREIGN KEY (arte_final_id)
            REFERENCES dbo.arte_finales(id) ON DELETE CASCADE,
        CONSTRAINT FK_arte_final_envios_correo FOREIGN KEY (correo_id)
            REFERENCES dbo.correos(id) ON DELETE SET NULL,
        CONSTRAINT FK_arte_final_envios_zip FOREIGN KEY (zip_documento_id)
            REFERENCES dbo.documentos(id) ON DELETE SET NULL
    );
END;

IF OBJECT_ID('dbo.comercial_vinculo', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.comercial_vinculo (
        presencia_user_id INT NOT NULL PRIMARY KEY,
        bc_comercial_id NVARCHAR(50) NULL,
        comercial NVARCHAR(255) NOT NULL,
        updated_at DATETIME2 NOT NULL CONSTRAINT DF_comercial_vinculo_updated DEFAULT SYSUTCDATETIME()
    );
END;
