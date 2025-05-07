# feather_users
CREATE TABLE `feather_users` (
  `user_idx` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `mid` CHAR(24) DEFAULT NULL,                       
  `handle` VARCHAR(100) NOT NULL,                    
  `name` VARCHAR(100),                               
  `email` VARCHAR(255),                              
  `image` LONGBLOB,                                  
  `date_created` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `agree_time` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  
  `agree_email` BOOLEAN DEFAULT FALSE,               
  `agree_push` BOOLEAN DEFAULT FALSE,                
  `is_deleted` BOOLEAN DEFAULT FALSE,                
  PRIMARY KEY (`user_idx`),
  UNIQUE KEY `uniq_handle` (`handle`)                
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE `feather_user_auth` (
  `auth_idx` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_idx` BIGINT UNSIGNED NOT NULL,               
  `provider` VARCHAR(50) NOT NULL,                   
  `sub` VARCHAR(255) NOT NULL,                       
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0,        
  PRIMARY KEY (`auth_idx`),
  UNIQUE KEY `uniq_provider_sub` (`provider`, `sub`),
  KEY `idx_user_idx` (`user_idx`),                   
  CONSTRAINT `fk_feather_user_auth_user_idx`
    FOREIGN KEY (`user_idx`) REFERENCES `feather_users`(`user_idx`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `feather_user_token` (
    `idx` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_idx` INT UNSIGNED NOT NULL,
    `iat` BIGINT NOT NULL,
    `device_idx` INT UNSIGNED NOT NULL,
    `remote_addr` VARCHAR(45) NOT NULL,
    `is_deleted` TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (`idx`),
    INDEX (`user_idx`),
    INDEX (`iat`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `feather_user_about` (
    `idx` INT UNSIGNED NOT NULL,
    `about` TEXT,
    `link_home` VARCHAR(255),
    `link_instagram` VARCHAR(255),
    `link_x` VARCHAR(255),
    `link_tiktok` VARCHAR(255),
    PRIMARY KEY (`idx`),
    CONSTRAINT `fk_feather_user_about_idx` FOREIGN KEY (`idx`) REFERENCES `feather_users`(`user_idx`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `feather_user_survey` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_idx` BIGINT UNSIGNED NOT NULL,
    `referral` VARCHAR(255),
    `occupation` VARCHAR(255),
    `fields` TEXT,
    `date_created` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_user` (`user_idx`),
    CONSTRAINT `fk_user_survey_user_idx` FOREIGN KEY (`user_idx`) REFERENCES `feather_users`(`user_idx`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE uploaded_files (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ulid VARCHAR(26) NOT NULL UNIQUE, -- ulid가 아니라wid 나 idx로 쓰는게 나을듯.
    -- ratio 추가 필요함 enum으로 '1/1', '4/3', '3/4'
    user_idx BIGINT NOT NULL,
    file_url TEXT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    tag VARCHAR(255),
    wip BOOLEAN DEFAULT FALSE,
    downloadable BOOLEAN DEFAULT TRUE,
    license ENUM('CC0', 'CC-BY', 'MIT', 'PROPRIETARY') DEFAULT NULL,
    thumbnail MEDIUMBLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_edited TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);