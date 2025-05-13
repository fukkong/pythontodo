-- 기존 DB SCHEMA
CREATE TABLE `feather_users` (
  `idx` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `mid` varchar(16) DEFAULT NULL,
  `handle` varchar(32) NOT NULL DEFAULT '',
  `name` varchar(190) NOT NULL DEFAULT '',
  `email` varchar(190) NOT NULL DEFAULT '',
  `image` varchar(190) DEFAULT NULL,
  `agree_email` tinyint(1) unsigned NOT NULL DEFAULT 0,
  `agree_push` tinyint(1) unsigned NOT NULL DEFAULT 0,
  `agree_time` timestamp NOT NULL DEFAULT current_timestamp(),
  `inserted_time` timestamp NOT NULL DEFAULT current_timestamp(),
  `is_deleted` tinyint(1) unsigned NOT NULL DEFAULT 0,
  PRIMARY KEY (`idx`),
  UNIQUE KEY `handle` (`handle`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `feather_user_auth` (
  `idx` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `user_idx` int(10) unsigned NOT NULL DEFAULT 0,
  `provider` varchar(16) NOT NULL DEFAULT '',
  `sub` varchar(190) NOT NULL DEFAULT '',
  `inserted_time` timestamp NOT NULL DEFAULT current_timestamp(),
  `is_deleted` tinyint(1) unsigned NOT NULL DEFAULT 0,
  PRIMARY KEY (`idx`),
  KEY `user_idx` (`user_idx`) USING BTREE,
  KEY `provider_sub` (`provider`,`sub`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `feather_user_token` (
  `idx` int(10) NOT NULL AUTO_INCREMENT,
  `user_idx` int(10) unsigned NOT NULL DEFAULT 0,
  `iat` int(10) unsigned NOT NULL DEFAULT 0,
  `device_idx` int(10) unsigned NOT NULL DEFAULT 0,
  `remote_addr` varchar(128) NOT NULL DEFAULT '',
  `is_deleted` tinyint(1) unsigned NOT NULL DEFAULT 0,
  PRIMARY KEY (`idx`)
) ENGINE=InnoDB AUTO_INCREMENT=28 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `feather_user_about` (
  `idx` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `about` text NOT NULL,
  `link_home` varchar(190) NOT NULL DEFAULT '',
  `link_instagram` varchar(190) NOT NULL DEFAULT '',
  `link_x` varchar(190) NOT NULL DEFAULT '',
  `link_tiktok` varchar(190) NOT NULL DEFAULT '',
  PRIMARY KEY (`idx`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `feather_user_survey` (
  `idx` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `user_idx` int(10) unsigned NOT NULL DEFAULT 0,
  `referral` varchar(128) NOT NULL DEFAULT '',
  `occupation` varchar(128) NOT NULL DEFAULT '',
  `fields` text NOT NULL,
  `inserted_time` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`idx`)
) ENGINE=InnoDB AUTO_INCREMENT=19 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `feather_devices` (
  `idx` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `env` varchar(8) NOT NULL DEFAULT '',
  `uuid` char(36) NOT NULL DEFAULT '',
  `push_token` varchar(255) DEFAULT NULL,
  `product` varchar(32) NOT NULL DEFAULT '',
  `os_version` varchar(32) NOT NULL DEFAULT '',
  `app_build` varchar(32) NOT NULL DEFAULT '',
  `web_build` varchar(32) NOT NULL DEFAULT '',
  `lang` varchar(32) NOT NULL DEFAULT '',
  `timezone` varchar(64) NOT NULL DEFAULT '',
  `remote_addr` varchar(190) NOT NULL DEFAULT '',
  `user_idx` int(10) unsigned DEFAULT NULL,
  `group` varchar(32) NOT NULL DEFAULT '',
  `memo` varchar(128) NOT NULL DEFAULT '',
  `inserted_time` timestamp NOT NULL DEFAULT current_timestamp(),
  `last_checkin_time` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`idx`),
  UNIQUE KEY `uuid` (`uuid`) USING BTREE,
  KEY `user_idx` (`user_idx`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=210 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

 CREATE TABLE `feather_handle_denylist` (
  `handle` varchar(32) NOT NULL DEFAULT '',
  PRIMARY KEY (`handle`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `feather_user_deletion` (
  `idx` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `user_idx` int(10) unsigned NOT NULL DEFAULT 0,
  `inserted_time` timestamp NOT NULL DEFAULT current_timestamp(),
  `canceled_time` timestamp NULL DEFAULT NULL,
  `deleted_time` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`idx`),
  KEY `user_idx` (`user_idx`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `share_notes` (
  `idx` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `share_idx` int(10) unsigned NOT NULL DEFAULT 0,
  `user_idx` int(10) unsigned NOT NULL DEFAULT 0,
  `relpath` varchar(190) NOT NULL DEFAULT '',
  `title` varchar(190) NOT NULL DEFAULT '',
  `size` int(10) unsigned NOT NULL DEFAULT 0,
  `created_time` timestamp NOT NULL DEFAULT  current_timestamp(),
  `modified_time` timestamp NOT NULL DEFAULT  current_timestamp(),
  `meta_changed` tinyint(1) unsigned NOT NULL DEFAULT 0,
  `file_key` varchar(190) NOT NULL DEFAULT '',
  `thumbnail_key` varchar(190) NOT NULL DEFAULT '',
  `inserted_time` timestamp NOT NULL DEFAULT current_timestamp(),
  `is_deleted` tinyint(1) unsigned NOT NULL DEFAULT 0,
  PRIMARY KEY (`idx`),
  KEY `share_idx_relpath` (`share_idx`,`relpath`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `share_root` (
  `idx` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `sid` varchar(32) NOT NULL DEFAULT '',
  `name` varchar(64) NOT NULL DEFAULT '',
  `icon` longtext DEFAULT NULL,
  `region` varchar(32) NOT NULL DEFAULT '',
  `bucket` varchar(128) NOT NULL DEFAULT '',
  `is_deleted` int(10) unsigned NOT NULL DEFAULT 0,
  PRIMARY KEY (`idx`),
  UNIQUE KEY `sid` (`sid`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `share_users` (
  `idx` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `user_idx` int(10) unsigned NOT NULL DEFAULT 0,
  `share_idx` int(10) unsigned NOT NULL DEFAULT 0,
  `role` tinyint(3) unsigned NOT NULL DEFAULT 0,
  `inserted_time` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`idx`),
  KEY `user_idx` (`user_idx`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- GALLERY DB SCHEMA
CREATE TABLE feather_gallery_works (
  `idx` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `wid` VARCHAR(26) NOT NULL UNIQUE,
  `ratio` ENUM('1/1','5/7','7/5') DEFAULT '1/1',
  `user_idx` int(10) unsigned NOT NULL DEFAULT 0,
  `file_url` VARCHAR(190) NOT NULL,
  `title` VARCHAR(190) NOT NULL,
  `description` TEXT,
  `wip` BOOLEAN DEFAULT FALSE,
  `downloadable` BOOLEAN DEFAULT TRUE,
  `license` ENUM('CC BY','CC BY-NC','CC BY-ND','CC BY-SA','CC BY-NC-SA','CC BY-NC-ND') DEFAULT NULL,
  `thumbnail` VARCHAR(190) NOT NULL,
  `is_deleted` tinyint(1) unsigned NOT NULL DEFAULT 0,
  `inserted_time` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `modified_time` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`idx`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE gallery_work_likes (
  `idx` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `user_idx` int(10) unsigned NOT NULL DEFAULT 0,
  `wid` VARCHAR(26) NOT NULL,
  `inserted_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`idx`),
  UNIQUE KEY uq_user_post (user_idx, wid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE gallery_work_downloads (
  `idx` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `user_idx` int(10) unsigned NOT NULL DEFAULT 0,
  `wid` VARCHAR(26) NOT NULL,
  `ip_address` VARCHAR(45),
  `user_agent` TEXT,
  `inserted_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`idx`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE gallery_tags (
  `idx` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `tag` VARCHAR(50) NOT NULL UNIQUE,
  `inserted_time` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`idx`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE gallery_work_tags (
  `wid` VARCHAR(26) NOT NULL,
  `tid` INT NOT NULL,
  PRIMARY KEY (wid, tid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE gallery_comments (
  `idx` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `wid` CHAR(26) NOT NULL,
  `parent_id` int(10) unsigned DEFAULT NULL,
  `user_idx` int(10) unsigned NOT NULL DEFAULT 0,
  `content` TEXT NOT NULL,
  `is_deleted` BOOLEAN DEFAULT FALSE,
  `inserted_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `modified_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`idx`),
  INDEX (wid),
  INDEX (parent_id),
  INDEX (user_idx)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
