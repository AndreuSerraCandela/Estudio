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
