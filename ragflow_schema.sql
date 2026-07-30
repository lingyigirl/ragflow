-- MySQL dump 10.13  Distrib 5.7.24, for Linux (x86_64)
--
-- Host: 172.19.70.234    Database: rag_flow
-- ------------------------------------------------------
-- Server version	8.0.39

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Current Database: `rag_flow`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `rag_flow` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;

USE `rag_flow`;

--
-- Table structure for table `ai_finance_template`
--

DROP TABLE IF EXISTS `ai_finance_template`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ai_finance_template` (
  `id` char(32) NOT NULL,
  `report_nm_cn` varchar(255) DEFAULT NULL COMMENT '报表中文名称',
  `report_nm_en` varchar(255) NOT NULL COMMENT '报表英文名称',
  `report_type` varchar(255) NOT NULL COMMENT '报表类型',
  `cust_type` varchar(255) NOT NULL COMMENT '客户类型',
  `index_nm_cn` varchar(255) NOT NULL COMMENT '指标中文名称',
  `index_nm_en` varchar(255) NOT NULL COMMENT '指标英文名称',
  `row_num` varchar(20) DEFAULT NULL COMMENT '目标行次',
  `write_title` varchar(20) DEFAULT NULL COMMENT '标题',
  `write_cood` varchar(20) DEFAULT NULL COMMENT '标题数值坐标',
  `create_user` varchar(20) DEFAULT NULL COMMENT '创建人',
  `created_at` datetime DEFAULT NULL COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  `update_user` varchar(20) DEFAULT NULL COMMENT '更新人',
  `del_ind` varchar(20) DEFAULT NULL COMMENT '删除标识',
  `parent_id` varchar(255) DEFAULT NULL COMMENT '上级指标ID',
  PRIMARY KEY (`id`),
  KEY `ix_ai_finance_template_report_type` (`report_type`),
  KEY `ix_ai_finance_template_id` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ai_finance_type`
--

DROP TABLE IF EXISTS `ai_finance_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ai_finance_type` (
  `id` char(32) NOT NULL,
  `report_nm_cn` varchar(200) DEFAULT NULL COMMENT '报表中文名称',
  `report_type` varchar(3) DEFAULT NULL COMMENT '报表类型',
  `cust_type` varchar(3) DEFAULT NULL COMMENT '客户类型',
  `head_json_info` varchar(2000) DEFAULT NULL COMMENT '表头信息',
  `file_path` varchar(1000) DEFAULT NULL COMMENT '文件路径',
  `create_user` varchar(64) DEFAULT NULL COMMENT '创建人',
  `update_user` varchar(64) DEFAULT NULL COMMENT '更新人',
  `created_at` datetime DEFAULT NULL COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  `del_ind` varchar(2) DEFAULT NULL COMMENT '删除标识',
  PRIMARY KEY (`id`),
  KEY `ix_ai_finance_type_id` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ai_indicators_custom`
--

DROP TABLE IF EXISTS `ai_indicators_custom`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ai_indicators_custom` (
  `id` varchar(32) NOT NULL COMMENT '主键',
  `name_cn` varchar(255) DEFAULT NULL COMMENT '中文名',
  `name_en` varchar(255) DEFAULT NULL COMMENT '英文名',
  `description` text COMMENT '描述',
  `source` varchar(50) DEFAULT NULL COMMENT '来源database；formula',
  `table_name` varchar(255) DEFAULT NULL COMMENT '表名',
  `index_group` varchar(128) DEFAULT NULL COMMENT '指标分类；主要业绩；偿债能力；经营能力；盈利能力；运营能力',
  `period` varchar(128) DEFAULT NULL COMMENT '期初值, 期末值, 上年同期值',
  `data_type` varchar(32) DEFAULT NULL COMMENT '数据类型；percentage；decimal；currency',
  `formula` text COMMENT '公式',
  `variables` text COMMENT '变量',
  `formula_part` varchar(2000) DEFAULT NULL COMMENT '公式变量数组（包含变量、数字、操作符）',
  `cust_type` varchar(4) DEFAULT NULL COMMENT '客户类型',
  `report_type` varchar(4) DEFAULT NULL COMMENT '财报类型',
  `mapping_type` varchar(4) DEFAULT NULL COMMENT '映射类型(01-映射 02-勾稽关系）',
  `created_at` datetime DEFAULT NULL COMMENT '创建日期',
  `create_user` varchar(64) DEFAULT NULL COMMENT '创建人',
  `updated_at` datetime DEFAULT NULL COMMENT '更新日期',
  `update_user` varchar(64) DEFAULT NULL COMMENT '更新人',
  `del_ind` varchar(2) DEFAULT NULL COMMENT '删除标识',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `api_4_conversation`
--

DROP TABLE IF EXISTS `api_4_conversation`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `api_4_conversation` (
  `id` varchar(32) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `dialog_id` varchar(32) NOT NULL,
  `user_id` varchar(255) NOT NULL,
  `message` longtext,
  `reference` longtext,
  `tokens` int NOT NULL,
  `source` varchar(16) DEFAULT NULL,
  `dsl` longtext,
  `duration` float NOT NULL,
  `round` int NOT NULL,
  `thumb_up` int NOT NULL,
  `errors` text,
  PRIMARY KEY (`id`),
  KEY `api4conversation_create_time` (`create_time`),
  KEY `api4conversation_create_date` (`create_date`),
  KEY `api4conversation_update_time` (`update_time`),
  KEY `api4conversation_update_date` (`update_date`),
  KEY `api4conversation_dialog_id` (`dialog_id`),
  KEY `api4conversation_user_id` (`user_id`),
  KEY `api4conversation_source` (`source`),
  KEY `api4conversation_duration` (`duration`),
  KEY `api4conversation_round` (`round`),
  KEY `api4conversation_thumb_up` (`thumb_up`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `api_token`
--

DROP TABLE IF EXISTS `api_token`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `api_token` (
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `tenant_id` varchar(32) NOT NULL,
  `token` varchar(255) NOT NULL,
  `dialog_id` varchar(32) DEFAULT NULL,
  `source` varchar(16) DEFAULT NULL,
  `beta` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`tenant_id`,`token`),
  KEY `apitoken_create_time` (`create_time`),
  KEY `apitoken_create_date` (`create_date`),
  KEY `apitoken_update_time` (`update_time`),
  KEY `apitoken_update_date` (`update_date`),
  KEY `apitoken_tenant_id` (`tenant_id`),
  KEY `apitoken_token` (`token`),
  KEY `apitoken_dialog_id` (`dialog_id`),
  KEY `apitoken_source` (`source`),
  KEY `apitoken_beta` (`beta`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `b_analysis_tasks`
--

DROP TABLE IF EXISTS `b_analysis_tasks`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `b_analysis_tasks` (
  `id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '主键ID',
  `com_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '客户ID/企业统一社会信用代码',
  `task_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '任务名称，如“2026年5月住宅电费导入”',
  `task_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '任务类型：SINGLE（单张）, BATCH（批量）, COMPARISON（对比）',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'PENDING' COMMENT '任务状态：PENDING, PROCESSING, COMPLETED, PARTIAL_FAILED',
  `create_user` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '创建人',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_user` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '创建人',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_status` (`status`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='分析任务表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `b_bill_documents`
--

DROP TABLE IF EXISTS `b_bill_documents`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `b_bill_documents` (
  `id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '主键，文档ID',
  `task_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '任务ID，关联 b_analysis_tasks.id',
  `com_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '客户ID/企业统一社会信用代码',
  `doc_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '客户ID/企业统一社会信用代码',
  `file_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '原始文件名',
  `file_path` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件存储路径或对象存储URL',
  `file_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件类型：JPG, PNG, PDF',
  `bill_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '账单类型：ELECTRIC（电费）, WATER（水费）',
  `recognition_status` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '整单识别状态：PENDING, SUCCESS, PARTIAL, FAILURE',
  `recognition_time` datetime DEFAULT NULL COMMENT '识别完成时间',
  `processing_status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'UPLOADED' COMMENT '文档处理流程状态：UPLOADED, OCR_DONE, COMPLETED',
  `upload_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  `recognition_progress` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '识别进度',
  `create_user` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '创建人',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_user` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '创建人',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_task_id` (`task_id`),
  KEY `idx_bill_type` (`bill_type`),
  KEY `idx_recognition_status` (`recognition_status`),
  CONSTRAINT `fk_bill_documents_task` FOREIGN KEY (`task_id`) REFERENCES `b_analysis_tasks` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='账单文档表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `b_extraction_field_configs`
--

DROP TABLE IF EXISTS `b_extraction_field_configs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `b_extraction_field_configs` (
  `id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '主键ID',
  `bill_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '适用账单类型：ELECTRIC, WATER, ALL',
  `field_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '字段键名，如 meter_number',
  `field_label` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '字段中文显示名，如“用电户号”',
  `field_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'STRING' COMMENT '字段值类型：STRING, NUMBER, DATE, BOOLEAN',
  `is_required` tinyint NOT NULL DEFAULT '0' COMMENT '是否必提：1-是，0-否',
  `group_name` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT '基本信息' COMMENT '字段分组，便于页面展示',
  `sort_order` int NOT NULL DEFAULT '0' COMMENT '同组内排序权重，越小越靠前',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'ACTIVE' COMMENT '状态：ACTIVE（启用）, DISABLED（禁用）',
  `description` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '字段备注说明',
  `create_user` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '创建人',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_user` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '创建人',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_bill_field` (`bill_type`,`field_name`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='提取字段配置表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `b_recognition_results`
--

DROP TABLE IF EXISTS `b_recognition_results`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `b_recognition_results` (
  `id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '主键ID',
  `task_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '任务ID，关联 analysis_tasks.id（冗余）',
  `com_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '客户ID/企业统一社会信用代码',
  `document_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文档ID，关联 bill_documents.id',
  `field_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '字段键名，对应配置表的 field_name',
  `field_value` text COLLATE utf8mb4_unicode_ci COMMENT '识别提取出的字段值',
  `corrected_value` text COLLATE utf8mb4_unicode_ci COMMENT '人工修正后的值（无修正时为 NULL）',
  `corrected_by` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '修正人',
  `corrected_at` datetime DEFAULT NULL COMMENT '修正时间',
  `create_user` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '创建人',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_user` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '创建人',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_doc_field` (`document_id`,`field_name`),
  KEY `idx_task_field` (`task_id`,`field_name`),
  KEY `idx_field_name` (`field_name`),
  CONSTRAINT `fk_recognition_results_document` FOREIGN KEY (`document_id`) REFERENCES `b_bill_documents` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_recognition_results_task` FOREIGN KEY (`task_id`) REFERENCES `b_analysis_tasks` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='识别结果表（窄表设计，每个字段一行）';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `canvas_template`
--

DROP TABLE IF EXISTS `canvas_template`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `canvas_template` (
  `id` varchar(32) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `avatar` text,
  `title` longtext,
  `description` longtext,
  `canvas_type` varchar(32) DEFAULT NULL,
  `canvas_category` varchar(32) NOT NULL,
  `dsl` longtext,
  PRIMARY KEY (`id`),
  KEY `canvastemplate_create_time` (`create_time`),
  KEY `canvastemplate_create_date` (`create_date`),
  KEY `canvastemplate_update_time` (`update_time`),
  KEY `canvastemplate_update_date` (`update_date`),
  KEY `canvastemplate_canvas_type` (`canvas_type`),
  KEY `canvastemplate_canvas_category` (`canvas_category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `child_chunk`
--

DROP TABLE IF EXISTS `child_chunk`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `child_chunk` (
  `id` varchar(128) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `parent_chunk_id` varchar(128) NOT NULL,
  `doc_id` varchar(128) NOT NULL,
  `kb_id` varchar(128) NOT NULL,
  `content` text NOT NULL,
  `content_ltks` text NOT NULL,
  `chunk_order_in_parent` int NOT NULL,
  `chunk_order_global` int NOT NULL,
  `page_num` int DEFAULT NULL,
  `position_int` int NOT NULL,
  `metadata` text NOT NULL,
  `token_count` int NOT NULL,
  `char_count` int NOT NULL,
  `img_id` varchar(128) DEFAULT NULL,
  `title_tks` text NOT NULL,
  `important_kwd` text NOT NULL,
  `available_int` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `childchunk_create_time` (`create_time`),
  KEY `childchunk_create_date` (`create_date`),
  KEY `childchunk_update_time` (`update_time`),
  KEY `childchunk_update_date` (`update_date`),
  KEY `childchunk_parent_chunk_id` (`parent_chunk_id`),
  KEY `childchunk_doc_id` (`doc_id`),
  KEY `childchunk_kb_id` (`kb_id`),
  KEY `childchunk_parent_chunk_id_chunk_order_in_parent` (`parent_chunk_id`,`chunk_order_in_parent`),
  KEY `childchunk_doc_id_chunk_order_global` (`doc_id`,`chunk_order_global`),
  KEY `childchunk_kb_id_available_int` (`kb_id`,`available_int`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `connector`
--

DROP TABLE IF EXISTS `connector`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `connector` (
  `id` varchar(32) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `tenant_id` varchar(32) NOT NULL,
  `name` varchar(128) NOT NULL,
  `source` varchar(128) NOT NULL,
  `input_type` varchar(128) NOT NULL,
  `config` longtext NOT NULL,
  `refresh_freq` int NOT NULL,
  `prune_freq` int NOT NULL,
  `timeout_secs` int NOT NULL,
  `indexing_start` datetime DEFAULT NULL,
  `status` varchar(16) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `connector_create_time` (`create_time`),
  KEY `connector_create_date` (`create_date`),
  KEY `connector_update_time` (`update_time`),
  KEY `connector_update_date` (`update_date`),
  KEY `connector_tenant_id` (`tenant_id`),
  KEY `connector_source` (`source`),
  KEY `connector_input_type` (`input_type`),
  KEY `connector_indexing_start` (`indexing_start`),
  KEY `connector_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `connector2kb`
--

DROP TABLE IF EXISTS `connector2kb`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `connector2kb` (
  `id` varchar(32) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `connector_id` varchar(32) NOT NULL,
  `kb_id` varchar(32) NOT NULL,
  `auto_parse` varchar(1) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `connector2kb_create_time` (`create_time`),
  KEY `connector2kb_create_date` (`create_date`),
  KEY `connector2kb_update_time` (`update_time`),
  KEY `connector2kb_update_date` (`update_date`),
  KEY `connector2kb_connector_id` (`connector_id`),
  KEY `connector2kb_kb_id` (`kb_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `conversation`
--

DROP TABLE IF EXISTS `conversation`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `conversation` (
  `id` varchar(32) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `dialog_id` varchar(32) NOT NULL,
  `name` varchar(255) DEFAULT NULL,
  `message` longtext,
  `reference` longtext,
  `user_id` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `conversation_create_time` (`create_time`),
  KEY `conversation_create_date` (`create_date`),
  KEY `conversation_update_time` (`update_time`),
  KEY `conversation_update_date` (`update_date`),
  KEY `conversation_dialog_id` (`dialog_id`),
  KEY `conversation_name` (`name`),
  KEY `conversation_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `db_balance_sheet`
--

DROP TABLE IF EXISTS `db_balance_sheet`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `db_balance_sheet` (
  `id` int NOT NULL AUTO_INCREMENT,
  `com_id` varchar(50) DEFAULT NULL COMMENT '统一社会信用代码',
  `year` varchar(20) DEFAULT NULL COMMENT '年度',
  `end_type` varchar(10) DEFAULT NULL COMMENT '报告期类型',
  `user_id` varchar(20) DEFAULT NULL COMMENT '用户id',
  `status` varchar(2) DEFAULT NULL COMMENT '数据状态：0、未验证未生效，1、已验证已生效',
  `updated_by` varchar(100) DEFAULT NULL COMMENT '更新人',
  `report_time` varchar(20) DEFAULT NULL COMMENT '报表生成日期',
  `is_consolidated_statements` varchar(20) NOT NULL COMMENT '是否合并报表',
  `category_assets` varchar(64) DEFAULT NULL COMMENT '一、资产类',
  `current_assets` varchar(64) DEFAULT NULL COMMENT '流动资产',
  `cash_and_cash_equivalents` varchar(64) DEFAULT NULL COMMENT '货币资金',
  `short_term_investments` varchar(64) DEFAULT NULL COMMENT '短期投资',
  `trading_financial_assets` varchar(64) DEFAULT NULL COMMENT '交易性金融资产',
  `notes_receivable` varchar(64) DEFAULT NULL COMMENT '应收票据',
  `dividends_receivable` varchar(64) DEFAULT NULL COMMENT '应收股利',
  `interest_receivable` varchar(64) DEFAULT NULL COMMENT '应收利息',
  `guarantee_fees_receivable` varchar(64) DEFAULT NULL COMMENT '应收担保费',
  `reinsurance_accounts_receivable` varchar(64) DEFAULT NULL COMMENT '应收分担保账款',
  `reinsurance_contract_reserves_receivable` varchar(64) DEFAULT NULL COMMENT '应收分保合同准备金',
  `compensation_payable_receivable` varchar(64) DEFAULT NULL COMMENT '应收代偿款',
  `guarantee_loss_subsidies_receivable` varchar(64) DEFAULT NULL COMMENT '应收担保损失补贴款',
  `other_receivables` varchar(64) DEFAULT NULL COMMENT '其他应收款',
  `allowance_for_bad_debts` varchar(64) DEFAULT NULL COMMENT '坏账准备',
  `prepaid_expenses` varchar(64) DEFAULT NULL COMMENT '待摊费用',
  `deposits_paid` varchar(64) DEFAULT NULL COMMENT '存出保证金',
  `reinsurance_deposits_paid` varchar(64) DEFAULT NULL COMMENT '存出分担保保证金',
  `entrusted_loans` varchar(64) DEFAULT NULL COMMENT '委托贷款',
  `provision_for_entrusted_loans` varchar(64) DEFAULT NULL COMMENT '委托贷款减值准备',
  `non_current_assets_due_within_one_year` varchar(64) DEFAULT NULL COMMENT '一年内到期的非流动资产',
  `other_current_assets` varchar(64) DEFAULT NULL COMMENT '其他流动资产',
  `total_current_assets` varchar(64) DEFAULT NULL COMMENT '流动资产合计',
  `non_current_assets` varchar(64) DEFAULT NULL COMMENT '非流动资产',
  `fixed_assets_original_cost` varchar(64) DEFAULT NULL COMMENT '固定资产原价',
  `accumulated_depreciation` varchar(64) DEFAULT NULL COMMENT '累计折旧',
  `fixed_assets_net_value` varchar(64) DEFAULT NULL COMMENT '固定资产净值',
  `long_term_prepaid_expenses` varchar(64) DEFAULT NULL COMMENT '长期待摊费用',
  `leasehold_improvements` varchar(64) DEFAULT NULL COMMENT '经营租入固定资产改良',
  `intangible_assets` varchar(64) DEFAULT NULL COMMENT '无形资产',
  `provision_for_intangible_assets` varchar(64) DEFAULT NULL COMMENT '无形资产减值准备',
  `unrecognized_financing_costs` varchar(64) DEFAULT NULL COMMENT '未确认融资费用',
  `pending_property_profit_and_loss` varchar(64) DEFAULT NULL COMMENT '待处理财产损益',
  `collateral_assets` varchar(64) DEFAULT NULL COMMENT '抵债资产',
  `provision_for_collateral_assets` varchar(64) DEFAULT NULL COMMENT '抵债资产减值准备',
  `long_term_equity_investments` varchar(64) DEFAULT NULL COMMENT '长期股权投资',
  `long_term_debt_investments` varchar(64) DEFAULT NULL COMMENT '长期债权投资',
  `other_long_term_assets` varchar(64) DEFAULT NULL COMMENT '其他长期资产',
  `provision_for_long_term_investments` varchar(64) DEFAULT NULL COMMENT '长期投资减值准备',
  `other_non_current_assets` varchar(64) DEFAULT NULL COMMENT '其他非流动资产',
  `total_non_current_assets` varchar(64) DEFAULT NULL COMMENT '非流动资产合计',
  `total_assets` varchar(64) DEFAULT NULL COMMENT '资产合计',
  `category_liabilities` varchar(64) DEFAULT NULL COMMENT '二、负债类',
  `current_liabilities` varchar(64) DEFAULT NULL COMMENT '流动负债',
  `short_term_loans` varchar(64) DEFAULT NULL COMMENT '短期借款',
  `accounts_payable` varchar(64) DEFAULT NULL COMMENT '应付款项',
  `guarantee_fees_received_in_advance` varchar(64) DEFAULT NULL COMMENT '预收担保费',
  `guarantee_deposits_received` varchar(64) DEFAULT NULL COMMENT '存入担保保证金',
  `reinsurance_deposits_received` varchar(64) DEFAULT NULL COMMENT '存入分担保保证金',
  `wages_payable` varchar(64) DEFAULT NULL COMMENT '应付工资',
  `welfare_payable` varchar(64) DEFAULT NULL COMMENT '应付福利费',
  `dividends_payable` varchar(64) DEFAULT NULL COMMENT '应付股利',
  `reinsurance_accounts_payable` varchar(64) DEFAULT NULL COMMENT '应付分保账款',
  `taxes_and_surcharges_payable` varchar(64) DEFAULT NULL COMMENT '应交税金及附加',
  `other_payables` varchar(64) DEFAULT NULL COMMENT '其它应付款',
  `accrued_expenses` varchar(64) DEFAULT NULL COMMENT '预提费用',
  `provision_for_guarantee_compensation` varchar(64) DEFAULT NULL COMMENT '担保赔偿准备',
  `unearned_premium_reserve` varchar(64) DEFAULT NULL COMMENT '未到期责任准备',
  `deferred_asset_value` varchar(64) DEFAULT NULL COMMENT '待转资产价值',
  `insurance_contract_reserves` varchar(64) DEFAULT NULL COMMENT '保险合同准备金',
  `other_current_liabilities` varchar(64) DEFAULT NULL COMMENT '其他流动负债',
  `total_current_liabilities` varchar(64) DEFAULT NULL COMMENT '流动负债合计',
  `non_current_liabilities` varchar(64) DEFAULT NULL COMMENT '非流动负债',
  `insurance_liability_reserves` varchar(64) DEFAULT NULL COMMENT '保险责任准备金',
  `long_term_loans` varchar(64) DEFAULT NULL COMMENT '长期借款',
  `long_term_accounts_payable` varchar(64) DEFAULT NULL COMMENT '长期应付款',
  `long_term_employee_benefits_payable` varchar(64) DEFAULT NULL COMMENT '长期应付职工薪酬',
  `special_payables` varchar(64) DEFAULT NULL COMMENT '专项应付款',
  `estimated_liabilities` varchar(64) DEFAULT NULL COMMENT '预计负债',
  `deferred_income` varchar(64) DEFAULT NULL COMMENT '递延收益',
  `deferred_tax_liabilities` varchar(64) DEFAULT NULL COMMENT '递延所得税负债',
  `other_non_current_liabilities` varchar(64) DEFAULT NULL COMMENT '其他非流动负债',
  `total_non_current_liabilities` varchar(64) DEFAULT NULL COMMENT '非流动负债合计',
  `total_liabilities` varchar(64) DEFAULT NULL COMMENT '负债合计',
  `category_owners_equity` varchar(64) DEFAULT NULL COMMENT '三、所有者权益',
  `paid_in_capital` varchar(64) DEFAULT NULL COMMENT '实收资本',
  `capital_surplus` varchar(64) DEFAULT NULL COMMENT '资本公积',
  `surplus_reserve` varchar(64) DEFAULT NULL COMMENT '盈余公积',
  `general_risk_preparation` varchar(64) DEFAULT NULL COMMENT '一般风险准备',
  `undistributed_profits` varchar(64) DEFAULT NULL COMMENT '未分配利润',
  `guarantee_support_fund` varchar(64) DEFAULT NULL COMMENT '担保扶持基金',
  `other_equity_instruments` varchar(64) DEFAULT NULL COMMENT '其他权益工具',
  `other_comprehensive_income` varchar(64) DEFAULT NULL COMMENT '其他综合收益',
  `special_reserve` varchar(64) DEFAULT NULL COMMENT '专项储备',
  `total_owners_equity` varchar(64) DEFAULT NULL COMMENT '所有者权益合计',
  `total_liabilities_and_owners_equity` varchar(64) DEFAULT NULL COMMENT '负债和所有者权益总计',
  `created_at` datetime NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_db_balance_sheet_com_id` (`com_id`),
  KEY `ix_db_balance_sheet_year` (`year`),
  KEY `ix_db_balance_sheet_id` (`id`),
  KEY `ix_db_balance_sheet_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `db_cashflow`
--

DROP TABLE IF EXISTS `db_cashflow`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `db_cashflow` (
  `id` int NOT NULL AUTO_INCREMENT,
  `com_id` varchar(50) DEFAULT NULL COMMENT '统一社会信用代码',
  `year` varchar(20) DEFAULT NULL COMMENT '年度',
  `end_type` varchar(10) DEFAULT NULL COMMENT '报告期类型',
  `user_id` varchar(20) DEFAULT NULL COMMENT '用户id',
  `status` varchar(2) DEFAULT NULL COMMENT '数据状态：0、未验证未生效，1、已验证已生效',
  `updated_by` varchar(100) DEFAULT NULL COMMENT '更新人',
  `report_time` varchar(20) DEFAULT NULL COMMENT '报表生成日期',
  `is_consolidated_statements` varchar(20) NOT NULL COMMENT '是否合并报表',
  `category_cash_flows_from_operating_activities` varchar(64) DEFAULT NULL COMMENT '一、经营活动产生的现金流量：',
  `cash_received_from_guarantee_fees` varchar(64) DEFAULT NULL COMMENT '收到的担保费收入',
  `refund_of_taxes_received` varchar(64) DEFAULT NULL COMMENT '收到的税费返还',
  `cash_received_from_insurance_premiums` varchar(64) DEFAULT NULL COMMENT '收到原保险合同保费取得的现金',
  `net_cash_received_from_reinsurance` varchar(64) DEFAULT NULL COMMENT '收到再保业务现金净额',
  `net_increase_in_policy_holders_deposits` varchar(64) DEFAULT NULL COMMENT '保户储金及投资款净增加额',
  `other_cash_received_related_to_operations` varchar(64) DEFAULT NULL COMMENT '收到其他与经营活动有关的现金',
  `subtotal_of_cash_inflows_from_operations` varchar(64) DEFAULT NULL COMMENT '经营活动现金流入小计',
  `cash_paid_for_guarantee_compensations` varchar(64) DEFAULT NULL COMMENT '担保代偿支付的现金',
  `cash_paid_for_insurance_claims` varchar(64) DEFAULT NULL COMMENT '支付原保险合同赔付款项的现金',
  `cash_paid_for_policy_dividends` varchar(64) DEFAULT NULL COMMENT '支付保单红利的现金',
  `cash_paid_to_and_for_employees` varchar(64) DEFAULT NULL COMMENT '支付给职工以及为职工支付的现金',
  `cash_paid_for_taxes` varchar(64) DEFAULT NULL COMMENT '支付的各项税费',
  `other_cash_paid_related_to_operations` varchar(64) DEFAULT NULL COMMENT '支付其他与经营活动有关的现金',
  `subtotal_of_cash_outflows_from_operations` varchar(64) DEFAULT NULL COMMENT '经营活动现金流出小计',
  `net_cash_flows_from_operating_activities` varchar(64) DEFAULT NULL COMMENT '经营活动产生的现金流量净额',
  `category_cash_flows_from_investing_activities` varchar(64) DEFAULT NULL COMMENT '二、投资活动产生的现金流量：',
  `cash_received_from_returns_on_investments` varchar(64) DEFAULT NULL COMMENT '收回投资所收到的现金',
  `cash_received_from_investment_income` varchar(64) DEFAULT NULL COMMENT '取得投资收益所收到的现金',
  `net_cash_received_from_disposal_of_assets` varchar(64) DEFAULT NULL COMMENT '处置固定资产、无形资产和其他长期资产所收回的现金净额',
  `other_cash_received_related_to_investments` varchar(64) DEFAULT NULL COMMENT '收到其他与投资活动有关的现金',
  `subtotal_of_cash_inflows_from_investments` varchar(64) DEFAULT NULL COMMENT '投资活动现金流入小计',
  `cash_paid_for_acquiring_assets` varchar(64) DEFAULT NULL COMMENT '购建固定资产、无形资产和其他长期资产所支付的现金',
  `cash_paid_for_investments` varchar(64) DEFAULT NULL COMMENT '投资所支付的现金',
  `other_cash_paid_related_to_investments` varchar(64) DEFAULT NULL COMMENT '支付的其他与投资活动有关的现金',
  `subtotal_of_cash_outflows_from_investments` varchar(64) DEFAULT NULL COMMENT '投资活动现金流出小计',
  `net_cash_flows_from_investing_activities` varchar(64) DEFAULT NULL COMMENT '投资活动产生的现金流量净额',
  `category_cash_flows_from_financing_activities` varchar(64) DEFAULT NULL COMMENT '三、筹资活动产生的现金流量：',
  `cash_received_from_capital_contributions` varchar(64) DEFAULT NULL COMMENT '吸收投资收到的现金',
  `cash_received_from_borrowings` varchar(64) DEFAULT NULL COMMENT '取得借款收到的现金',
  `other_cash_received_related_to_financing` varchar(64) DEFAULT NULL COMMENT '收到其他与筹资活动有关的现金',
  `subtotal_of_cash_inflows_from_financing` varchar(64) DEFAULT NULL COMMENT '筹资活动现金流入小计',
  `cash_repayments_of_borrowings` varchar(64) DEFAULT NULL COMMENT '偿还债务支付的现金',
  `cash_paid_for_dividends_and_interest` varchar(64) DEFAULT NULL COMMENT '分配股利、利润或偿付利息支付的现金',
  `other_cash_paid_related_to_financing` varchar(64) DEFAULT NULL COMMENT '支付其他与筹资活动有关的现金',
  `subtotal_of_cash_outflows_from_financing` varchar(64) DEFAULT NULL COMMENT '筹资活动现金流出小计',
  `net_cash_flows_from_financing_activities` varchar(64) DEFAULT NULL COMMENT '筹资活动产生的现金流量净额',
  `category_effect_of_foreign_exchange_rate` varchar(64) DEFAULT NULL COMMENT '四、汇率变动对现金及现金等价物的影响',
  `net_increase_in_cash_and_equivalents` varchar(64) DEFAULT NULL COMMENT '五、现金及现金等价物净增加额',
  `cash_and_equivalents_at_beginning` varchar(64) DEFAULT NULL COMMENT '加：期初现金及现金等价物余额',
  `cash_and_equivalents_at_end` varchar(64) DEFAULT NULL COMMENT '六、期末现金及现金等价物余额',
  `current_period_amount` varchar(64) DEFAULT NULL COMMENT '本期数',
  `cumulative_amount` varchar(64) DEFAULT NULL COMMENT '累计数',
  `created_at` datetime NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_db_cashflow_user_id` (`user_id`),
  KEY `ix_db_cashflow_com_id` (`com_id`),
  KEY `ix_db_cashflow_id` (`id`),
  KEY `ix_db_cashflow_year` (`year`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `db_income`
--

DROP TABLE IF EXISTS `db_income`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `db_income` (
  `id` int NOT NULL AUTO_INCREMENT,
  `com_id` varchar(50) DEFAULT NULL COMMENT '统一社会信用代码',
  `year` varchar(20) DEFAULT NULL COMMENT '年度',
  `end_type` varchar(10) DEFAULT NULL COMMENT '报告期类型',
  `user_id` varchar(20) DEFAULT NULL COMMENT '用户id',
  `status` varchar(2) DEFAULT NULL COMMENT '数据状态：0、未验证未生效，1、已验证已生效',
  `updated_by` varchar(100) DEFAULT NULL COMMENT '更新人',
  `report_time` varchar(20) DEFAULT NULL COMMENT '报表生成日期',
  `is_consolidated_statements` varchar(20) NOT NULL COMMENT '是否合并报表',
  `operating_revenue` varchar(64) DEFAULT NULL COMMENT '营业收入',
  `guarantee_business_cost` varchar(64) DEFAULT NULL COMMENT '担保业务成本',
  `net_interest_income` varchar(64) DEFAULT NULL COMMENT '利息净收入',
  `interest_income` varchar(64) DEFAULT NULL COMMENT '利息收入',
  `interest_expense` varchar(64) DEFAULT NULL COMMENT '利息支出',
  `net_fee_income` varchar(64) DEFAULT NULL COMMENT '手续费净收入',
  `fee_income` varchar(64) DEFAULT NULL COMMENT '手续费收入',
  `fee_expense` varchar(64) DEFAULT NULL COMMENT '手续费支出',
  `net_commission_income` varchar(64) DEFAULT NULL COMMENT '佣金净收入',
  `commission_income` varchar(64) DEFAULT NULL COMMENT '佣金收入',
  `commission_expense` varchar(64) DEFAULT NULL COMMENT '佣金支出',
  `guarantee_fee_income` varchar(64) DEFAULT NULL COMMENT '担保费收入',
  `review_fee_income` varchar(64) DEFAULT NULL COMMENT '评审费收入',
  `recovery_income` varchar(64) DEFAULT NULL COMMENT '追偿收入',
  `other_income` varchar(64) DEFAULT NULL COMMENT '其他收入',
  `investment_income` varchar(64) DEFAULT NULL COMMENT '投资收益',
  `fair_value_change_income` varchar(64) DEFAULT NULL COMMENT '公允价值变动收益',
  `exchange_gains` varchar(64) DEFAULT NULL COMMENT '汇兑收益',
  `business_tax_and_surcharges` varchar(64) DEFAULT NULL COMMENT '营业税金及附加',
  `operating_expenses` varchar(64) DEFAULT NULL COMMENT '营业费用',
  `policy_dividend_expenses` varchar(64) DEFAULT NULL COMMENT '保单红利支出',
  `reinsurance_fee_expenses` varchar(64) DEFAULT NULL COMMENT '分担保费支出',
  `guarantee_compensation_expenses` varchar(64) DEFAULT NULL COMMENT '担保赔偿支出',
  `asset_impairment_loss` varchar(64) DEFAULT NULL COMMENT '资产减值损失',
  `net_change_in_insurance_contract_reserves` varchar(64) DEFAULT NULL COMMENT '提取保险合同准备金净额',
  `other_expenses` varchar(64) DEFAULT NULL COMMENT '其他支出',
  `operating_profit` varchar(64) DEFAULT NULL COMMENT '营业利润',
  `non_operating_income` varchar(64) DEFAULT NULL COMMENT '营业外收入',
  `non_operating_expenses` varchar(64) DEFAULT NULL COMMENT '营业外支出',
  `total_profit` varchar(64) DEFAULT NULL COMMENT '利润总额',
  `income_tax_expense` varchar(64) DEFAULT NULL COMMENT '所得税费用',
  `net_profit` varchar(64) DEFAULT NULL COMMENT '净利润',
  `current_period_amount` varchar(64) DEFAULT NULL COMMENT '本期数',
  `cumulative_amount` varchar(64) DEFAULT NULL COMMENT '累计数',
  `created_at` datetime NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_db_income_year` (`year`),
  KEY `ix_db_income_com_id` (`com_id`),
  KEY `ix_db_income_user_id` (`user_id`),
  KEY `ix_db_income_id` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `dialog`
--

DROP TABLE IF EXISTS `dialog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `dialog` (
  `id` varchar(32) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `tenant_id` varchar(32) NOT NULL,
  `name` varchar(255) DEFAULT NULL,
  `description` text,
  `icon` text,
  `language` varchar(32) DEFAULT NULL,
  `llm_id` varchar(128) NOT NULL,
  `llm_setting` longtext NOT NULL,
  `prompt_type` varchar(16) NOT NULL,
  `prompt_config` longtext NOT NULL,
  `meta_data_filter` longtext,
  `similarity_threshold` float NOT NULL,
  `vector_similarity_weight` float NOT NULL,
  `top_n` int NOT NULL,
  `top_k` int NOT NULL,
  `do_refer` varchar(1) NOT NULL,
  `rerank_id` varchar(128) NOT NULL,
  `kb_ids` longtext NOT NULL,
  `status` varchar(1) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `dialog_create_time` (`create_time`),
  KEY `dialog_create_date` (`create_date`),
  KEY `dialog_update_time` (`update_time`),
  KEY `dialog_update_date` (`update_date`),
  KEY `dialog_tenant_id` (`tenant_id`),
  KEY `dialog_name` (`name`),
  KEY `dialog_language` (`language`),
  KEY `dialog_prompt_type` (`prompt_type`),
  KEY `dialog_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `document`
--

DROP TABLE IF EXISTS `document`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `document` (
  `id` varchar(32) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `thumbnail` text,
  `kb_id` varchar(256) NOT NULL,
  `parser_id` varchar(32) NOT NULL,
  `pipeline_id` varchar(32) DEFAULT NULL,
  `parser_config` longtext NOT NULL,
  `source_type` varchar(128) NOT NULL,
  `type` varchar(32) NOT NULL,
  `created_by` varchar(32) NOT NULL,
  `name` varchar(255) DEFAULT NULL,
  `location` varchar(255) DEFAULT NULL,
  `size` int NOT NULL,
  `token_num` int NOT NULL,
  `chunk_num` int NOT NULL,
  `progress` float NOT NULL,
  `progress_msg` text,
  `process_begin_at` datetime DEFAULT NULL,
  `process_duration` float NOT NULL,
  `meta_fields` longtext,
  `suffix` varchar(32) NOT NULL,
  `run` varchar(1) DEFAULT NULL,
  `status` varchar(1) DEFAULT NULL,
  `voucher_type` varchar(64) DEFAULT NULL,
  `llm_classify_success` tinyint(1) NOT NULL,
  `voucher_type_confidence` float DEFAULT NULL,
  `voucher_type_source` varchar(16) DEFAULT NULL,
  `llm_name` varchar(255) DEFAULT NULL,
  `llm_content` longtext,
  `tree` longtext,
  `tree_cross_ref` longtext,
  `sha256_hash` varchar(64) DEFAULT NULL,
  `doc_type_en` varchar(128) DEFAULT NULL,
  `doc_type_cn` varchar(128) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `document_create_time` (`create_time`),
  KEY `document_create_date` (`create_date`),
  KEY `document_update_time` (`update_time`),
  KEY `document_update_date` (`update_date`),
  KEY `document_kb_id` (`kb_id`),
  KEY `document_parser_id` (`parser_id`),
  KEY `document_pipeline_id` (`pipeline_id`),
  KEY `document_source_type` (`source_type`),
  KEY `document_type` (`type`),
  KEY `document_created_by` (`created_by`),
  KEY `document_name` (`name`),
  KEY `document_location` (`location`),
  KEY `document_size` (`size`),
  KEY `document_token_num` (`token_num`),
  KEY `document_chunk_num` (`chunk_num`),
  KEY `document_progress` (`progress`),
  KEY `document_process_begin_at` (`process_begin_at`),
  KEY `document_suffix` (`suffix`),
  KEY `document_run` (`run`),
  KEY `document_status` (`status`),
  KEY `document_voucher_type` (`voucher_type`),
  KEY `document_voucher_type_source` (`voucher_type_source`),
  KEY `document_llm_name` (`llm_name`),
  KEY `document_sha256_hash` (`sha256_hash`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `edoc_classification`
--

DROP TABLE IF EXISTS `edoc_classification`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `edoc_classification` (
  `id` varchar(20) NOT NULL,
  `com_id` varchar(128) DEFAULT NULL COMMENT '统一社会信用代码',
  `library_id` varchar(128) DEFAULT NULL COMMENT '用于第三方的知识库id唯一标准',
  `user_id` varchar(128) DEFAULT NULL COMMENT '用户id',
  `pid` varchar(128) DEFAULT NULL COMMENT '用于创建目录数，否则前一个节点id',
  `class_cn` varchar(128) DEFAULT NULL COMMENT '目录名称',
  `end_type` varchar(20) NOT NULL COMMENT '报告期',
  `year` varchar(20) NOT NULL COMMENT '年度',
  `progress` varchar(16) DEFAULT NULL COMMENT '提取进度',
  `task_id` varchar(128) DEFAULT NULL COMMENT '任务id',
  `created_at` datetime DEFAULT NULL COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `ix_edoc_classification_year` (`year`),
  KEY `ix_edoc_classification_id` (`id`),
  KEY `ix_edoc_classification_end_type` (`end_type`),
  KEY `ix_edoc_classification_library_id` (`library_id`),
  KEY `ix_edoc_classification_com_id` (`com_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='知识库层级';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `edoc_document`
--

DROP TABLE IF EXISTS `edoc_document`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `edoc_document` (
  `id` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  `kb_id` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '用于第三方的知识库id唯一标准',
  `doc_id` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '用于第三方的文档id唯一标准',
  `progress` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '进度',
  `user_id` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '用户id',
  `task_id` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '任务ID',
  `com_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '公司全称',
  `com_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '统一社会信用代码',
  `end_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '报告期',
  `year` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '年度',
  `file_name` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '文件名称',
  `root_path` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '目录路径',
  `title` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '公告标题',
  `path` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '保存路径',
  `ann_date` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '公告日期',
  `ts_code` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '股票代码',
  `name` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '股票名称',
  `url` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '公告链接',
  `rec_time` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '公告发布时间',
  `created_at` datetime DEFAULT NULL COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  `preview_url` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `report_scope` varchar(20) COLLATE utf8mb4_bin DEFAULT NULL COMMENT '报表口径（01-单一、02-合并）',
  `report_end_date` varchar(30) COLLATE utf8mb4_bin DEFAULT NULL COMMENT '报表截止日期',
  PRIMARY KEY (`id`),
  KEY `ix_edoc_document_id` (`id`),
  KEY `ix_edoc_document_ts_code` (`ts_code`),
  KEY `ix_edoc_document_end_type` (`end_type`),
  KEY `ix_edoc_document_year` (`year`),
  KEY `ix_edoc_document_com_id` (`com_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='财报报表文档信息表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `edoc_library`
--

DROP TABLE IF EXISTS `edoc_library`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `edoc_library` (
  `id` varchar(20) NOT NULL COMMENT 'id',
  `kb_id` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '用于第三方的知识库id唯一标准',
  `user_id` varchar(128) DEFAULT NULL COMMENT '用户id',
  `com_name` varchar(100) DEFAULT NULL COMMENT '公司全称',
  `com_id` varchar(50) NOT NULL COMMENT '统一社会信用代码',
  `ts_code` varchar(20) DEFAULT NULL COMMENT '股票代码',
  `exchange` varchar(20) DEFAULT NULL COMMENT '交易所代码',
  `chairman` varchar(50) DEFAULT NULL COMMENT '法人代表',
  `manager` varchar(50) DEFAULT NULL COMMENT '总经理',
  `secretary` varchar(50) DEFAULT NULL COMMENT '董秘',
  `reg_capital` varchar(200) DEFAULT NULL COMMENT '注册资本(万元)',
  `setup_date` varchar(20) DEFAULT NULL COMMENT '注册日期',
  `province` varchar(50) DEFAULT NULL COMMENT '所在省份',
  `city` varchar(50) DEFAULT NULL COMMENT '所在城市',
  `introduction` text COMMENT '公司介绍',
  `website` varchar(200) DEFAULT NULL COMMENT '公司主页',
  `email` varchar(100) DEFAULT NULL COMMENT '电子邮件',
  `office` varchar(200) DEFAULT NULL COMMENT '办公室',
  `employees` varchar(200) DEFAULT NULL COMMENT '员工人数',
  `main_business` text COMMENT '主要业务及产品',
  `business_scope` text COMMENT '经营范围',
  `cust_type` varchar(50) DEFAULT NULL COMMENT '客户类型-字典类型：cust_type',
  `created_at` datetime NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  `is_deleted` tinyint(1) DEFAULT NULL COMMENT '软删除标记：0-未删除、1-已删除',
  `create_user` varchar(4) DEFAULT NULL COMMENT '创建人',
  `update_user` varchar(4) DEFAULT NULL COMMENT '更新人',
  PRIMARY KEY (`id`),
  KEY `ix_edoc_library_id` (`id`),
  KEY `ix_edoc_library_ts_code` (`ts_code`),
  KEY `ix_edoc_library_user_id` (`user_id`),
  KEY `ix_edoc_library_com_name` (`com_name`),
  KEY `ix_edoc_library_library_id` (`kb_id`),
  KEY `ix_edoc_library_com_id` (`com_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='知识库对应的公司详情';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `edoc_tasks`
--

DROP TABLE IF EXISTS `edoc_tasks`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `edoc_tasks` (
  `id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '任务ID',
  `com_id` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '公司ID',
  `type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '01-财报上传文件,02-财报提取数据,03-财报数据分析',
  `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '任务状态（默认：PENDING, STARTED, SUCCESS, FAILURE, TIMEOUT）',
  `progress` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '任务进度',
  `params` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '任务参数',
  `result` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '任务结果',
  `user_id` varchar(128) DEFAULT NULL COMMENT '用户id',
  `created_at` datetime NOT NULL COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  `main_task_id` varchar(64) DEFAULT NULL COMMENT '主任务ID',
  `start_time` datetime DEFAULT NULL COMMENT '开始执行时间',
  `end_time` datetime DEFAULT NULL COMMENT '执行结束时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_edoc_tasks_id` (`id`),
  KEY `ix_edoc_tasks_user_id` (`user_id`),
  KEY `ix_edoc_tasks_com_id` (`com_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `evaluation_cases`
--

DROP TABLE IF EXISTS `evaluation_cases`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `evaluation_cases` (
  `id` varchar(32) NOT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `dataset_id` varchar(32) NOT NULL,
  `question` text NOT NULL,
  `reference_answer` text,
  `relevant_doc_ids` longtext,
  `relevant_chunk_ids` longtext,
  `metadata` longtext,
  `create_time` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `evaluationcase_create_date` (`create_date`),
  KEY `evaluationcase_update_time` (`update_time`),
  KEY `evaluationcase_update_date` (`update_date`),
  KEY `evaluationcase_dataset_id` (`dataset_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `evaluation_datasets`
--

DROP TABLE IF EXISTS `evaluation_datasets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `evaluation_datasets` (
  `id` varchar(32) NOT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `tenant_id` varchar(32) NOT NULL,
  `name` varchar(255) NOT NULL,
  `description` text,
  `kb_ids` longtext NOT NULL,
  `created_by` varchar(32) NOT NULL,
  `create_time` bigint NOT NULL,
  `update_time` bigint NOT NULL,
  `status` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `evaluationdataset_create_date` (`create_date`),
  KEY `evaluationdataset_update_date` (`update_date`),
  KEY `evaluationdataset_tenant_id` (`tenant_id`),
  KEY `evaluationdataset_name` (`name`),
  KEY `evaluationdataset_created_by` (`created_by`),
  KEY `evaluationdataset_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `evaluation_results`
--

DROP TABLE IF EXISTS `evaluation_results`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `evaluation_results` (
  `id` varchar(32) NOT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `run_id` varchar(32) NOT NULL,
  `case_id` varchar(32) NOT NULL,
  `generated_answer` text NOT NULL,
  `retrieved_chunks` longtext NOT NULL,
  `metrics` longtext NOT NULL,
  `execution_time` float NOT NULL,
  `token_usage` longtext,
  `create_time` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `evaluationresult_create_date` (`create_date`),
  KEY `evaluationresult_update_time` (`update_time`),
  KEY `evaluationresult_update_date` (`update_date`),
  KEY `evaluationresult_run_id` (`run_id`),
  KEY `evaluationresult_case_id` (`case_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `evaluation_runs`
--

DROP TABLE IF EXISTS `evaluation_runs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `evaluation_runs` (
  `id` varchar(32) NOT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `dataset_id` varchar(32) NOT NULL,
  `dialog_id` varchar(32) NOT NULL,
  `name` varchar(255) NOT NULL,
  `config_snapshot` longtext NOT NULL,
  `metrics_summary` longtext,
  `status` varchar(32) NOT NULL,
  `created_by` varchar(32) NOT NULL,
  `create_time` bigint NOT NULL,
  `complete_time` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `evaluationrun_create_date` (`create_date`),
  KEY `evaluationrun_update_time` (`update_time`),
  KEY `evaluationrun_update_date` (`update_date`),
  KEY `evaluationrun_dataset_id` (`dataset_id`),
  KEY `evaluationrun_dialog_id` (`dialog_id`),
  KEY `evaluationrun_created_by` (`created_by`),
  KEY `evaluationrun_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `file`
--

DROP TABLE IF EXISTS `file`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `file` (
  `id` varchar(32) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `parent_id` varchar(32) NOT NULL,
  `tenant_id` varchar(32) NOT NULL,
  `created_by` varchar(32) NOT NULL,
  `name` varchar(255) NOT NULL,
  `location` varchar(255) DEFAULT NULL,
  `size` int NOT NULL,
  `type` varchar(32) NOT NULL,
  `source_type` varchar(128) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `file_create_time` (`create_time`),
  KEY `file_create_date` (`create_date`),
  KEY `file_update_time` (`update_time`),
  KEY `file_update_date` (`update_date`),
  KEY `file_parent_id` (`parent_id`),
  KEY `file_tenant_id` (`tenant_id`),
  KEY `file_created_by` (`created_by`),
  KEY `file_name` (`name`),
  KEY `file_location` (`location`),
  KEY `file_size` (`size`),
  KEY `file_type` (`type`),
  KEY `file_source_type` (`source_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `file2document`
--

DROP TABLE IF EXISTS `file2document`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `file2document` (
  `id` varchar(32) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `file_id` varchar(32) DEFAULT NULL,
  `document_id` varchar(32) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `file2document_create_time` (`create_time`),
  KEY `file2document_create_date` (`create_date`),
  KEY `file2document_update_time` (`update_time`),
  KEY `file2document_update_date` (`update_date`),
  KEY `file2document_file_id` (`file_id`),
  KEY `file2document_document_id` (`document_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `gen_table`
--

DROP TABLE IF EXISTS `gen_table`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `gen_table` (
  `table_id` bigint NOT NULL AUTO_INCREMENT COMMENT '编号',
  `table_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '表名称',
  `table_comment` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '表描述',
  `sub_table_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '关联子表的表名',
  `sub_table_fk_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '子表关联的外键名',
  `class_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '实体类名称',
  `tpl_category` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'crud' COMMENT '使用的模板（crud单表操作 tree树表操作）',
  `tpl_web_type` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '前端模板类型（element-ui模版 element-plus模版）',
  `package_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '生成包路径',
  `module_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '生成模块名',
  `business_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '生成业务名',
  `function_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '生成功能名',
  `function_author` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '生成功能作者',
  `gen_type` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '0' COMMENT '生成代码方式（0zip压缩包 1自定义路径）',
  `gen_path` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '/' COMMENT '生成路径（不填默认项目路径）',
  `options` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '其它生成选项',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`table_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='代码生成业务表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `gen_table_column`
--

DROP TABLE IF EXISTS `gen_table_column`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `gen_table_column` (
  `column_id` bigint NOT NULL AUTO_INCREMENT COMMENT '编号',
  `table_id` bigint DEFAULT NULL COMMENT '归属表编号',
  `column_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '列名称',
  `column_comment` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '列描述',
  `column_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '列类型',
  `java_type` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'JAVA类型',
  `java_field` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'JAVA字段名',
  `is_pk` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '是否主键（1是）',
  `is_increment` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '是否自增（1是）',
  `is_required` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '是否必填（1是）',
  `is_insert` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '是否为插入字段（1是）',
  `is_edit` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '是否编辑字段（1是）',
  `is_list` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '是否列表字段（1是）',
  `is_query` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '是否查询字段（1是）',
  `query_type` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'EQ' COMMENT '查询方式（等于、不等于、大于、小于、范围）',
  `html_type` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '显示类型（文本框、文本域、下拉框、复选框、单选框、日期控件）',
  `dict_type` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '字典类型',
  `sort` int DEFAULT NULL COMMENT '排序',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`column_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='代码生成业务表字段';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `indicators_chart`
--

DROP TABLE IF EXISTS `indicators_chart`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `indicators_chart` (
  `id` varchar(255) NOT NULL,
  `name_cn` varchar(255) NOT NULL COMMENT '中文名称',
  `name_en` varchar(255) NOT NULL COMMENT '英文名称',
  `description` varchar(255) DEFAULT NULL COMMENT '描述',
  `source` varchar(255) NOT NULL COMMENT '数据来源',
  `data_type` varchar(255) NOT NULL COMMENT '数据类型归类',
  `chart_type` varchar(255) NOT NULL COMMENT '展示图形类型',
  `user_id` varchar(255) DEFAULT NULL COMMENT '用户id',
  `authority` varchar(255) DEFAULT NULL COMMENT '用户权限',
  `cust_type` varchar(20) DEFAULT NULL COMMENT '客户类型',
  `created_at` datetime NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_indicators_chart_data_type` (`data_type`),
  KEY `ix_indicators_chart_id` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `indicators_custom`
--

DROP TABLE IF EXISTS `indicators_custom`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `indicators_custom` (
  `id` varchar(255) NOT NULL,
  `name_cn` varchar(255) DEFAULT NULL COMMENT '中文名',
  `name_en` varchar(255) DEFAULT NULL COMMENT '英文名',
  `description` text COMMENT '描述',
  `source` varchar(50) DEFAULT NULL COMMENT '来源database；formula',
  `table_name` varchar(255) DEFAULT NULL COMMENT '表名',
  `type` varchar(32) DEFAULT NULL COMMENT '指标类型；0（自定义指标公式），1（勾稽关系公式）',
  `group` varchar(128) DEFAULT NULL COMMENT '指标分类；主要业绩；偿债能力；经营能力；盈利能力；运营能力',
  `period` varchar(128) DEFAULT NULL COMMENT '期初值, 期末值, 上年同期值',
  `data_type` varchar(32) DEFAULT NULL COMMENT '数据类型；percentage；decimal；currency',
  `formula` text COMMENT '公式',
  `variables` text COMMENT '变量',
  `display` varchar(4) DEFAULT NULL COMMENT '是否显示,1显示',
  `user_id` varchar(126) DEFAULT NULL COMMENT '用户id',
  `authority` varchar(4) NOT NULL COMMENT '权限,1共享',
  `updated_by` varchar(100) DEFAULT NULL COMMENT '更新人',
  `created_at` datetime NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_indicators_custom_user_id` (`user_id`),
  KEY `ix_indicators_custom_type` (`type`),
  KEY `ix_indicators_custom_group` (`group`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `indicators_financial`
--

DROP TABLE IF EXISTS `indicators_financial`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `indicators_financial` (
  `id` varchar(255) NOT NULL,
  `index` varchar(32) DEFAULT NULL COMMENT '索引',
  `name_cn` varchar(255) DEFAULT NULL COMMENT '中文名',
  `name_en` varchar(255) DEFAULT NULL COMMENT '英文名',
  `description` varchar(255) DEFAULT NULL COMMENT '描述',
  `data_type` varchar(255) DEFAULT NULL COMMENT '数据类型；percentage；decimal；currency',
  `group` varchar(255) DEFAULT NULL COMMENT '分类;利润，资产负债，现金流',
  `source` varchar(255) DEFAULT NULL COMMENT '来源',
  `table_name` varchar(255) DEFAULT NULL COMMENT '表名',
  `bold` varchar(4) DEFAULT NULL COMMENT '是否加粗显示',
  `show_id` varchar(4) DEFAULT NULL COMMENT '前端的显示效果（纯文本、可编辑文本）',
  `created_at` datetime NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `interface_input_param`
--

DROP TABLE IF EXISTS `interface_input_param`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `interface_input_param` (
  `id` varchar(36) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `interface_id` varchar(32) NOT NULL,
  `field_name_cn` varchar(255) DEFAULT NULL,
  `field_name_en` varchar(255) DEFAULT NULL,
  `field_type` varchar(32) DEFAULT NULL,
  `param_value_type` varchar(32) DEFAULT NULL,
  `param_value` text,
  `sort_order` int NOT NULL,
  `status` varchar(1) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `interfaceinputparam_create_time` (`create_time`),
  KEY `interfaceinputparam_create_date` (`create_date`),
  KEY `interfaceinputparam_update_time` (`update_time`),
  KEY `interfaceinputparam_update_date` (`update_date`),
  KEY `interfaceinputparam_interface_id` (`interface_id`),
  KEY `interfaceinputparam_interface_id_sort_order` (`interface_id`,`sort_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `interface_output_param`
--

DROP TABLE IF EXISTS `interface_output_param`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `interface_output_param` (
  `id` varchar(36) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `interface_id` varchar(32) NOT NULL,
  `param_name_cn` varchar(255) NOT NULL,
  `param_name_en` varchar(255) NOT NULL,
  `data_type` varchar(32) NOT NULL,
  `sort_order` int NOT NULL,
  `status` varchar(1) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `interfaceoutputparam_create_time` (`create_time`),
  KEY `interfaceoutputparam_create_date` (`create_date`),
  KEY `interfaceoutputparam_update_time` (`update_time`),
  KEY `interfaceoutputparam_update_date` (`update_date`),
  KEY `interfaceoutputparam_interface_id` (`interface_id`),
  KEY `interfaceoutputparam_interface_id_sort_order` (`interface_id`,`sort_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `invitation_code`
--

DROP TABLE IF EXISTS `invitation_code`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `invitation_code` (
  `id` varchar(32) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `code` varchar(32) NOT NULL,
  `visit_time` datetime DEFAULT NULL,
  `user_id` varchar(32) DEFAULT NULL,
  `tenant_id` varchar(32) DEFAULT NULL,
  `status` varchar(1) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `invitationcode_create_time` (`create_time`),
  KEY `invitationcode_create_date` (`create_date`),
  KEY `invitationcode_update_time` (`update_time`),
  KEY `invitationcode_update_date` (`update_date`),
  KEY `invitationcode_code` (`code`),
  KEY `invitationcode_visit_time` (`visit_time`),
  KEY `invitationcode_user_id` (`user_id`),
  KEY `invitationcode_tenant_id` (`tenant_id`),
  KEY `invitationcode_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `knowledgebase`
--

DROP TABLE IF EXISTS `knowledgebase`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `knowledgebase` (
  `id` varchar(32) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `avatar` text,
  `tenant_id` varchar(32) NOT NULL,
  `name` varchar(128) NOT NULL,
  `language` varchar(32) DEFAULT NULL,
  `description` text,
  `embd_id` varchar(128) NOT NULL,
  `permission` varchar(16) NOT NULL,
  `created_by` varchar(32) NOT NULL,
  `doc_num` int NOT NULL,
  `token_num` int NOT NULL,
  `chunk_num` int NOT NULL,
  `similarity_threshold` float NOT NULL,
  `vector_similarity_weight` float NOT NULL,
  `parser_id` varchar(32) NOT NULL,
  `pipeline_id` varchar(32) DEFAULT NULL,
  `parser_config` longtext NOT NULL,
  `pagerank` int NOT NULL,
  `graphrag_task_id` varchar(32) DEFAULT NULL,
  `graphrag_task_finish_at` datetime DEFAULT NULL,
  `raptor_task_id` varchar(32) DEFAULT NULL,
  `raptor_task_finish_at` datetime DEFAULT NULL,
  `mindmap_task_id` varchar(32) DEFAULT NULL,
  `mindmap_task_finish_at` datetime DEFAULT NULL,
  `status` varchar(1) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `knowledgebase_create_time` (`create_time`),
  KEY `knowledgebase_create_date` (`create_date`),
  KEY `knowledgebase_update_time` (`update_time`),
  KEY `knowledgebase_update_date` (`update_date`),
  KEY `knowledgebase_tenant_id` (`tenant_id`),
  KEY `knowledgebase_name` (`name`),
  KEY `knowledgebase_language` (`language`),
  KEY `knowledgebase_embd_id` (`embd_id`),
  KEY `knowledgebase_permission` (`permission`),
  KEY `knowledgebase_created_by` (`created_by`),
  KEY `knowledgebase_doc_num` (`doc_num`),
  KEY `knowledgebase_token_num` (`token_num`),
  KEY `knowledgebase_chunk_num` (`chunk_num`),
  KEY `knowledgebase_similarity_threshold` (`similarity_threshold`),
  KEY `knowledgebase_vector_similarity_weight` (`vector_similarity_weight`),
  KEY `knowledgebase_parser_id` (`parser_id`),
  KEY `knowledgebase_pipeline_id` (`pipeline_id`),
  KEY `knowledgebase_graphrag_task_id` (`graphrag_task_id`),
  KEY `knowledgebase_raptor_task_id` (`raptor_task_id`),
  KEY `knowledgebase_mindmap_task_id` (`mindmap_task_id`),
  KEY `knowledgebase_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `llm`
--

DROP TABLE IF EXISTS `llm`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `llm` (
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `llm_name` varchar(128) NOT NULL,
  `model_type` varchar(128) NOT NULL,
  `fid` varchar(128) NOT NULL,
  `max_tokens` int NOT NULL,
  `tags` varchar(255) NOT NULL,
  `is_tools` tinyint(1) NOT NULL,
  `status` varchar(1) DEFAULT NULL,
  PRIMARY KEY (`fid`,`llm_name`),
  KEY `llm_create_time` (`create_time`),
  KEY `llm_create_date` (`create_date`),
  KEY `llm_update_time` (`update_time`),
  KEY `llm_update_date` (`update_date`),
  KEY `llm_llm_name` (`llm_name`),
  KEY `llm_model_type` (`model_type`),
  KEY `llm_fid` (`fid`),
  KEY `llm_tags` (`tags`),
  KEY `llm_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `llm_factories`
--

DROP TABLE IF EXISTS `llm_factories`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `llm_factories` (
  `name` varchar(128) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `logo` text,
  `tags` varchar(255) NOT NULL,
  `rank` int NOT NULL,
  `status` varchar(1) DEFAULT NULL,
  PRIMARY KEY (`name`),
  KEY `llmfactories_create_time` (`create_time`),
  KEY `llmfactories_create_date` (`create_date`),
  KEY `llmfactories_update_time` (`update_time`),
  KEY `llmfactories_update_date` (`update_date`),
  KEY `llmfactories_tags` (`tags`),
  KEY `llmfactories_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `mcp_server`
--

DROP TABLE IF EXISTS `mcp_server`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `mcp_server` (
  `id` varchar(32) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `name` varchar(255) NOT NULL,
  `tenant_id` varchar(32) NOT NULL,
  `url` varchar(2048) NOT NULL,
  `server_type` varchar(32) NOT NULL,
  `description` text,
  `variables` longtext,
  `headers` longtext,
  PRIMARY KEY (`id`),
  KEY `mcpserver_create_time` (`create_time`),
  KEY `mcpserver_create_date` (`create_date`),
  KEY `mcpserver_update_time` (`update_time`),
  KEY `mcpserver_update_date` (`update_date`),
  KEY `mcpserver_tenant_id` (`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `memory`
--

DROP TABLE IF EXISTS `memory`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `memory` (
  `id` varchar(32) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `name` varchar(128) NOT NULL,
  `avatar` text,
  `tenant_id` varchar(32) NOT NULL,
  `memory_type` int NOT NULL,
  `storage_type` varchar(32) NOT NULL,
  `embd_id` varchar(128) NOT NULL,
  `llm_id` varchar(128) NOT NULL,
  `permissions` varchar(16) NOT NULL,
  `description` text,
  `memory_size` int NOT NULL,
  `forgetting_policy` varchar(32) NOT NULL,
  `temperature` float NOT NULL,
  `system_prompt` text,
  `user_prompt` text,
  PRIMARY KEY (`id`),
  KEY `memory_create_time` (`create_time`),
  KEY `memory_create_date` (`create_date`),
  KEY `memory_update_time` (`update_time`),
  KEY `memory_update_date` (`update_date`),
  KEY `memory_tenant_id` (`tenant_id`),
  KEY `memory_memory_type` (`memory_type`),
  KEY `memory_storage_type` (`storage_type`),
  KEY `memory_permissions` (`permissions`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `mineru_section`
--

DROP TABLE IF EXISTS `mineru_section`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `mineru_section` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `kb_id` varchar(64) NOT NULL,
  `doc_id` varchar(64) NOT NULL,
  `chunk_id` varchar(64) NOT NULL,
  `type` varchar(20) NOT NULL,
  `text` longtext,
  `bbox` longtext,
  `page_idx` int DEFAULT NULL,
  `text_level` int DEFAULT NULL,
  `img_path` varchar(512) DEFAULT NULL,
  `table_caption` longtext,
  `table_footnote` longtext,
  `table_body` longtext,
  `sub_type` varchar(50) DEFAULT NULL,
  `list_items` longtext,
  `parent_chain` longtext,
  `es_id` varchar(64) DEFAULT NULL,
  `es_tab2text` longtext,
  `llm_tab2text` longtext,
  PRIMARY KEY (`id`),
  KEY `minerusection_create_time` (`create_time`),
  KEY `minerusection_create_date` (`create_date`),
  KEY `minerusection_update_time` (`update_time`),
  KEY `minerusection_update_date` (`update_date`),
  KEY `minerusection_kb_id` (`kb_id`),
  KEY `minerusection_doc_id` (`doc_id`),
  KEY `minerusection_chunk_id` (`chunk_id`),
  KEY `mineru_section_es_id` (`es_id`)
) ENGINE=InnoDB AUTO_INCREMENT=9209745830684201923 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `model_form_filling`
--

DROP TABLE IF EXISTS `model_form_filling`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `model_form_filling` (
  `id` varchar(200) NOT NULL COMMENT '任务id',
  `status` varchar(20) DEFAULT NULL COMMENT '任务状态码，0：执行中，1：成功，2：失败',
  `param` text COMMENT '任务的请求入参',
  `err_msg` text COMMENT '任务失败原因',
  `data` json DEFAULT NULL COMMENT 'ai填充的结果，json格式',
  `created_at` datetime DEFAULT NULL COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_model_form_filling_id` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ocr_compare_sessions`
--

DROP TABLE IF EXISTS `ocr_compare_sessions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ocr_compare_sessions` (
  `id` varchar(32) NOT NULL COMMENT '主键ID (uuid hex)',
  `user_id` varchar(64) NOT NULL COMMENT '用户ID',
  `file_name` varchar(255) NOT NULL COMMENT '原始文件名',
  `file_type` varchar(20) NOT NULL COMMENT '文件扩展名',
  `status` varchar(20) NOT NULL DEFAULT 'PENDING' COMMENT '会话状态: PENDING/RUNNING/SUCCESS/PARTIAL/FAILED',
  `document_ids` text NOT NULL COMMENT '关联 document_id 列表 JSON 数组',
  `engine_ids` text NOT NULL COMMENT '引擎 ID 列表 JSON 数组',
  `summary_cache` mediumtext COMMENT '导出摘要缓存 JSON',
  `parse_options` text COMMENT '解析选项 JSON（全局一份）',
  `source` varchar(32) NOT NULL DEFAULT 'upload' COMMENT '来源: upload / from_documents',
  `created_at` datetime NOT NULL COMMENT '创建时间',
  `updated_at` datetime NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `ix_ocr_compare_sessions_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='OCR多引擎对比会话表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `parent_child_config`
--

DROP TABLE IF EXISTS `parent_child_config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `parent_child_config` (
  `kb_id` varchar(128) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `parent_chunk_size` int NOT NULL,
  `parent_chunk_overlap` int NOT NULL,
  `parent_separator` varchar(64) NOT NULL,
  `child_chunk_size` int NOT NULL,
  `child_chunk_overlap` int NOT NULL,
  `child_separator` varchar(64) NOT NULL,
  `retrieval_mode` varchar(16) NOT NULL,
  `top_k_children` int NOT NULL,
  `top_k_parents` int NOT NULL,
  `enabled` tinyint(1) NOT NULL,
  `config_json` text NOT NULL,
  PRIMARY KEY (`kb_id`),
  KEY `parentchildconfig_create_time` (`create_time`),
  KEY `parentchildconfig_create_date` (`create_date`),
  KEY `parentchildconfig_update_time` (`update_time`),
  KEY `parentchildconfig_update_date` (`update_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `parent_child_mapping`
--

DROP TABLE IF EXISTS `parent_child_mapping`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `parent_child_mapping` (
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `child_chunk_id` varchar(128) NOT NULL,
  `parent_chunk_id` varchar(128) NOT NULL,
  `doc_id` varchar(128) NOT NULL,
  `kb_id` varchar(128) NOT NULL,
  `relevance_score` int NOT NULL,
  UNIQUE KEY `parentchildmapping_child_chunk_id_parent_chunk_id` (`child_chunk_id`,`parent_chunk_id`),
  KEY `parentchildmapping_create_time` (`create_time`),
  KEY `parentchildmapping_create_date` (`create_date`),
  KEY `parentchildmapping_update_time` (`update_time`),
  KEY `parentchildmapping_update_date` (`update_date`),
  KEY `parentchildmapping_child_chunk_id` (`child_chunk_id`),
  KEY `parentchildmapping_parent_chunk_id` (`parent_chunk_id`),
  KEY `parentchildmapping_doc_id` (`doc_id`),
  KEY `parentchildmapping_kb_id` (`kb_id`),
  KEY `parentchildmapping_kb_id_doc_id` (`kb_id`,`doc_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `parent_chunk`
--

DROP TABLE IF EXISTS `parent_chunk`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `parent_chunk` (
  `id` varchar(128) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `doc_id` varchar(128) NOT NULL,
  `kb_id` varchar(128) NOT NULL,
  `content` text NOT NULL,
  `content_with_weight` text NOT NULL,
  `chunk_order` int NOT NULL,
  `page_num` int DEFAULT NULL,
  `metadata` text NOT NULL,
  `token_count` int NOT NULL,
  `char_count` int NOT NULL,
  `chunk_method` varchar(32) NOT NULL,
  `available_int` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `parentchunk_create_time` (`create_time`),
  KEY `parentchunk_create_date` (`create_date`),
  KEY `parentchunk_update_time` (`update_time`),
  KEY `parentchunk_update_date` (`update_date`),
  KEY `parentchunk_doc_id` (`doc_id`),
  KEY `parentchunk_kb_id` (`kb_id`),
  KEY `parentchunk_doc_id_chunk_order` (`doc_id`,`chunk_order`),
  KEY `parentchunk_kb_id_available_int` (`kb_id`,`available_int`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `pipeline_operation_log`
--

DROP TABLE IF EXISTS `pipeline_operation_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `pipeline_operation_log` (
  `id` varchar(32) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `document_id` varchar(32) NOT NULL,
  `tenant_id` varchar(32) NOT NULL,
  `kb_id` varchar(32) NOT NULL,
  `pipeline_id` varchar(32) DEFAULT NULL,
  `pipeline_title` varchar(32) DEFAULT NULL,
  `parser_id` varchar(32) NOT NULL,
  `document_name` varchar(255) NOT NULL,
  `document_suffix` varchar(255) NOT NULL,
  `document_type` varchar(255) NOT NULL,
  `source_from` varchar(255) NOT NULL,
  `progress` float NOT NULL,
  `progress_msg` text,
  `process_begin_at` datetime DEFAULT NULL,
  `process_duration` float NOT NULL,
  `dsl` longtext,
  `task_type` varchar(32) NOT NULL,
  `operation_status` varchar(32) NOT NULL,
  `avatar` text,
  `status` varchar(1) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `pipelineoperationlog_create_time` (`create_time`),
  KEY `pipelineoperationlog_create_date` (`create_date`),
  KEY `pipelineoperationlog_update_time` (`update_time`),
  KEY `pipelineoperationlog_update_date` (`update_date`),
  KEY `pipelineoperationlog_document_id` (`document_id`),
  KEY `pipelineoperationlog_tenant_id` (`tenant_id`),
  KEY `pipelineoperationlog_kb_id` (`kb_id`),
  KEY `pipelineoperationlog_pipeline_id` (`pipeline_id`),
  KEY `pipelineoperationlog_pipeline_title` (`pipeline_title`),
  KEY `pipelineoperationlog_parser_id` (`parser_id`),
  KEY `pipelineoperationlog_progress` (`progress`),
  KEY `pipelineoperationlog_process_begin_at` (`process_begin_at`),
  KEY `pipelineoperationlog_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `qy_balance_sheet`
--

DROP TABLE IF EXISTS `qy_balance_sheet`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `qy_balance_sheet` (
  `id` int NOT NULL AUTO_INCREMENT,
  `com_id` varchar(50) DEFAULT NULL COMMENT '统一社会信用代码',
  `year` varchar(20) DEFAULT NULL COMMENT '年度',
  `end_type` varchar(10) DEFAULT NULL COMMENT '报告期类型',
  `user_id` varchar(20) DEFAULT NULL COMMENT '用户id',
  `status` varchar(2) DEFAULT NULL COMMENT '数据状态：0、未验证未生效，1、已验证已生效',
  `updated_by` varchar(100) DEFAULT NULL COMMENT '更新人',
  `report_time` varchar(20) DEFAULT NULL COMMENT '报表生成日期',
  `is_consolidated_statements` varchar(20) NOT NULL COMMENT '是否合并报表',
  `category_assets` varchar(64) DEFAULT NULL COMMENT '一、资产类',
  `current_assets` varchar(64) DEFAULT NULL COMMENT '流动资产',
  `cash_and_cash_equivalents` varchar(64) DEFAULT NULL COMMENT '货币资金',
  `settlement_provisions` varchar(64) DEFAULT NULL COMMENT '结算备付金',
  `short_term_investments` varchar(64) DEFAULT NULL COMMENT '短期投资',
  `fiscal_reimbursement_quota` varchar(64) DEFAULT NULL COMMENT '财政应返还额度',
  `notes_receivable` varchar(64) DEFAULT NULL COMMENT '应收票据',
  `accounts_receivable` varchar(64) DEFAULT NULL COMMENT '应收账款',
  `subsidies_receivable` varchar(64) DEFAULT NULL COMMENT '应收补贴款',
  `premiums_receivable` varchar(64) DEFAULT NULL COMMENT '应收保费',
  `dividends_receivable` varchar(64) DEFAULT NULL COMMENT '应收股利',
  `interest_receivable` varchar(64) DEFAULT NULL COMMENT '应收利息',
  `other_receivables` varchar(64) DEFAULT NULL COMMENT '其他应收款',
  `inventory` varchar(64) DEFAULT NULL COMMENT '存货',
  `prepaid_expenses` varchar(64) DEFAULT NULL COMMENT '待摊费用',
  `prepayments` varchar(64) DEFAULT NULL COMMENT '预付账款',
  `non_current_assets_due_within_one_year` varchar(64) DEFAULT NULL COMMENT '一年内到期的非流动资产',
  `other_current_assets` varchar(64) DEFAULT NULL COMMENT '其他流动资产',
  `total_current_assets` varchar(64) DEFAULT NULL COMMENT '流动资产合计',
  `non_current_assets` varchar(64) DEFAULT NULL COMMENT '非流动资产',
  `long_term_equity_investments` varchar(64) DEFAULT NULL COMMENT '长期股权投资',
  `long_term_bond_investments` varchar(64) DEFAULT NULL COMMENT '长期债券投资',
  `fixed_assets` varchar(64) DEFAULT NULL COMMENT '固定资产',
  `construction_materials` varchar(64) DEFAULT NULL COMMENT '工程物资',
  `construction_in_progress` varchar(64) DEFAULT NULL COMMENT '在建工程',
  `intangible_assets` varchar(64) DEFAULT NULL COMMENT '无形资产',
  `rd_expenditure` varchar(64) DEFAULT NULL COMMENT '研发支出',
  `public_infrastructure` varchar(64) DEFAULT NULL COMMENT '公共基础设施',
  `government_reserve_materials` varchar(64) DEFAULT NULL COMMENT '政府储备物资',
  `cultural_relics_assets` varchar(64) DEFAULT NULL COMMENT '文物文化资产',
  `affordable_housing` varchar(64) DEFAULT NULL COMMENT '保障性住房',
  `long_term_prepaid_expenses` varchar(64) DEFAULT NULL COMMENT '长期待摊费用',
  `pending_property_losses` varchar(64) DEFAULT NULL COMMENT '待处理财产损溢',
  `other_non_current_assets` varchar(64) DEFAULT NULL COMMENT '其他非流动资产',
  `total_non_current_assets` varchar(64) DEFAULT NULL COMMENT '非流动资产合计',
  `trustee_agent_assets` varchar(64) DEFAULT NULL COMMENT '受托代理资产',
  `total_assets` varchar(64) DEFAULT NULL COMMENT '资产合计',
  `category_liabilities` varchar(64) DEFAULT NULL COMMENT '二、负债类',
  `current_liabilities` varchar(64) DEFAULT NULL COMMENT '流动负债',
  `short_term_loans` varchar(64) DEFAULT NULL COMMENT '短期借款',
  `vat_payable` varchar(64) DEFAULT NULL COMMENT '应交增值税',
  `other_taxes_payable` varchar(64) DEFAULT NULL COMMENT '其他应交税费',
  `payable_to_fiscal` varchar(64) DEFAULT NULL COMMENT '应缴财政款',
  `medical_settlement_payable` varchar(64) DEFAULT NULL COMMENT '待结算医疗款',
  `employee_benefits_payable` varchar(64) DEFAULT NULL COMMENT '应付职工薪酬',
  `notes_payable` varchar(64) DEFAULT NULL COMMENT '应付票据',
  `accounts_payable` varchar(64) DEFAULT NULL COMMENT '应付账款',
  `government_subsidies_payable` varchar(64) DEFAULT NULL COMMENT '应付政府补贴款',
  `interest_payable` varchar(64) DEFAULT NULL COMMENT '应付利息',
  `advances_from_customers` varchar(64) DEFAULT NULL COMMENT '预收账款',
  `other_payables` varchar(64) DEFAULT NULL COMMENT '其他应付款',
  `accrued_expenses` varchar(64) DEFAULT NULL COMMENT '预提费用',
  `non_current_liabilities_due_within_one_year` varchar(64) DEFAULT NULL COMMENT '一年内到期的非流动负债',
  `other_current_liabilities` varchar(64) DEFAULT NULL COMMENT '其他流动负债',
  `total_current_liabilities` varchar(64) DEFAULT NULL COMMENT '流动负债合计',
  `non_current_liabilities` varchar(64) DEFAULT NULL COMMENT '非流动负债',
  `long_term_loans` varchar(64) DEFAULT NULL COMMENT '长期借款',
  `long_term_payables` varchar(64) DEFAULT NULL COMMENT '长期应付款',
  `estimated_liabilities` varchar(64) DEFAULT NULL COMMENT '预计负债',
  `other_non_current_liabilities` varchar(64) DEFAULT NULL COMMENT '其他非流动负债',
  `total_non_current_liabilities` varchar(64) DEFAULT NULL COMMENT '非流动负债合计',
  `trustee_agent_liabilities` varchar(64) DEFAULT NULL COMMENT '受托代理负债',
  `total_liabilities` varchar(64) DEFAULT NULL COMMENT '负债合计',
  `category_net_assets` varchar(64) DEFAULT NULL COMMENT '三、净资产',
  `accumulated_surplus` varchar(64) DEFAULT NULL COMMENT '累计盈余',
  `fixed_fund` varchar(64) DEFAULT NULL COMMENT '固定基金',
  `investment_fund` varchar(64) DEFAULT NULL COMMENT '投资基金',
  `enterprise_fund` varchar(64) DEFAULT NULL COMMENT '事业基金',
  `special_fund` varchar(64) DEFAULT NULL COMMENT '专用基金',
  `equity_method_adjustment` varchar(64) DEFAULT NULL COMMENT '权益法调整',
  `net_assets_transferred_without_compensation` varchar(64) DEFAULT NULL COMMENT '无偿调拨净资产',
  `other_net_assets` varchar(64) DEFAULT NULL COMMENT '其他净资产',
  `total_net_assets` varchar(64) DEFAULT NULL COMMENT '净资产合计',
  `total_liabilities_and_net_assets` varchar(64) DEFAULT NULL COMMENT '负债和净资产合计',
  `created_at` datetime NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_qy_balance_sheet_user_id` (`user_id`),
  KEY `ix_qy_balance_sheet_id` (`id`),
  KEY `ix_qy_balance_sheet_com_id` (`com_id`),
  KEY `ix_qy_balance_sheet_year` (`year`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `qy_cashflow`
--

DROP TABLE IF EXISTS `qy_cashflow`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `qy_cashflow` (
  `id` int NOT NULL AUTO_INCREMENT,
  `com_id` varchar(50) DEFAULT NULL COMMENT '统一社会信用代码',
  `year` varchar(20) DEFAULT NULL COMMENT '年度',
  `end_type` varchar(10) DEFAULT NULL COMMENT '报告期类型',
  `user_id` varchar(20) DEFAULT NULL COMMENT '用户id',
  `status` varchar(2) DEFAULT NULL COMMENT '数据状态：0、未验证未生效，1、已验证已生效',
  `updated_by` varchar(100) DEFAULT NULL COMMENT '更新人',
  `report_time` varchar(20) DEFAULT NULL COMMENT '报表生成日期',
  `is_consolidated_statements` varchar(20) NOT NULL COMMENT '是否合并报表',
  `total_institutional_expenditure` varchar(64) DEFAULT NULL COMMENT '事业支出合计',
  `category_salary_and_welfare_expenses` varchar(64) DEFAULT NULL COMMENT '1、工资福利支出',
  `basic_salary` varchar(64) DEFAULT NULL COMMENT '基本工资',
  `allowances_and_subsidies` varchar(64) DEFAULT NULL COMMENT '津贴补贴',
  `bonuses` varchar(64) DEFAULT NULL COMMENT '奖金',
  `social_security_contributions` varchar(64) DEFAULT NULL COMMENT '社会保障缴费',
  `meal_expenses` varchar(64) DEFAULT NULL COMMENT '伙食费',
  `meal_allowances` varchar(64) DEFAULT NULL COMMENT '伙食补助费',
  `performance_based_pay` varchar(64) DEFAULT NULL COMMENT '绩效工资',
  `other_salary_and_welfare_expenses` varchar(64) DEFAULT NULL COMMENT '其他工资福利支出',
  `category_goods_and_services_expenses` varchar(64) DEFAULT NULL COMMENT '2、商品和服务支出',
  `office_expenses` varchar(64) DEFAULT NULL COMMENT '办公费',
  `printing_costs` varchar(64) DEFAULT NULL COMMENT '印刷费',
  `consulting_fees` varchar(64) DEFAULT NULL COMMENT '咨询费',
  `service_charges` varchar(64) DEFAULT NULL COMMENT '手续费',
  `water_charges` varchar(64) DEFAULT NULL COMMENT '水费',
  `electricity_charges` varchar(64) DEFAULT NULL COMMENT '电费',
  `postage_and_telecom` varchar(64) DEFAULT NULL COMMENT '邮电费',
  `heating_expenses` varchar(64) DEFAULT NULL COMMENT '取暖费',
  `property_management_fees` varchar(64) DEFAULT NULL COMMENT '物业管理费',
  `transportation_expenses` varchar(64) DEFAULT NULL COMMENT '交通费',
  `travel_expenses` varchar(64) DEFAULT NULL COMMENT '差旅费',
  `overseas_expenses` varchar(64) DEFAULT NULL COMMENT '出国费',
  `maintenance_costs` varchar(64) DEFAULT NULL COMMENT '维修（护）费',
  `rental_fees` varchar(64) DEFAULT NULL COMMENT '租赁费',
  `conference_fees` varchar(64) DEFAULT NULL COMMENT '会议费',
  `training_costs` varchar(64) DEFAULT NULL COMMENT '培训费',
  `entertainment_expenses` varchar(64) DEFAULT NULL COMMENT '招待费',
  `special_materials` varchar(64) DEFAULT NULL COMMENT '专用材料费',
  `uniform_purchases` varchar(64) DEFAULT NULL COMMENT '被装购置费',
  `special_fuel_costs` varchar(64) DEFAULT NULL COMMENT '专用燃料费',
  `labor_service_fees` varchar(64) DEFAULT NULL COMMENT '劳务费',
  `outsourcing_costs` varchar(64) DEFAULT NULL COMMENT '委托业务费',
  `trade_union_funds` varchar(64) DEFAULT NULL COMMENT '工会经费',
  `welfare_expenses` varchar(64) DEFAULT NULL COMMENT '福利费',
  `other_goods_and_services` varchar(64) DEFAULT NULL COMMENT '其他商品和劳务支出',
  `category_individual_and_family_allowances` varchar(64) DEFAULT NULL COMMENT '3、对个人和家庭的补助',
  `retirement_pension` varchar(64) DEFAULT NULL COMMENT '离休费',
  `pension_expenses` varchar(64) DEFAULT NULL COMMENT '退休费',
  `severance_pay` varchar(64) DEFAULT NULL COMMENT '退职（役）费',
  `compensation_payments` varchar(64) DEFAULT NULL COMMENT '抚恤金',
  `living_allowances` varchar(64) DEFAULT NULL COMMENT '生活补助',
  `relief_funds` varchar(64) DEFAULT NULL COMMENT '救济费',
  `medical_expenses` varchar(64) DEFAULT NULL COMMENT '医疗费',
  `student_stipends` varchar(64) DEFAULT NULL COMMENT '助学金',
  `incentive_awards` varchar(64) DEFAULT NULL COMMENT '奖励金',
  `production_subsidies` varchar(64) DEFAULT NULL COMMENT '生产补贴',
  `housing_provident_fund` varchar(64) DEFAULT NULL COMMENT '住房公积金',
  `housing_rent_allowance` varchar(64) DEFAULT NULL COMMENT '提租补贴',
  `housing_purchase_subsidy` varchar(64) DEFAULT NULL COMMENT '购房补贴',
  `other_individual_and_family_allowances` varchar(64) DEFAULT NULL COMMENT '其他对个人和家庭的补助支出',
  `category_enterprise_subsidies` varchar(64) DEFAULT NULL COMMENT '4、对企事业单位的补贴',
  `policy_based_enterprise_subsidies` varchar(64) DEFAULT NULL COMMENT '企业政策性补贴',
  `fiscal_interest_subsidies` varchar(64) DEFAULT NULL COMMENT '财政贴息',
  `institutional_unit_subsidies` varchar(64) DEFAULT NULL COMMENT '事业单位补贴',
  `other_enterprise_subsidies` varchar(64) DEFAULT NULL COMMENT '其他对企事业单位的补贴支出',
  `category_transfer_expenditures` varchar(64) DEFAULT NULL COMMENT '5、转移性支出',
  `intergovernmental_transfers` varchar(64) DEFAULT NULL COMMENT '不同级政府间转移性支出',
  `intragovernmental_transfers` varchar(64) DEFAULT NULL COMMENT '同级政府间转移性支出',
  `category_donations` varchar(64) DEFAULT NULL COMMENT '6、赠与',
  `domestic_donations` varchar(64) DEFAULT NULL COMMENT '对国内的赠与',
  `foreign_donations` varchar(64) DEFAULT NULL COMMENT '对国外的赠与',
  `category_debt_interest_expenses` varchar(64) DEFAULT NULL COMMENT '7、债务利息支出',
  `treasury_bond_interest` varchar(64) DEFAULT NULL COMMENT '国库券付息',
  `central_bank_loan_interest` varchar(64) DEFAULT NULL COMMENT '向国家银行借款利息',
  `other_domestic_bank_loan_interest` varchar(64) DEFAULT NULL COMMENT '其他国内银行借款利息',
  `foreign_government_loan_interest` varchar(64) DEFAULT NULL COMMENT '向国外政府借款利息',
  `international_organization_loan_interest` varchar(64) DEFAULT NULL COMMENT '向国际组织借款利息',
  `other_foreign_loan_interest` varchar(64) DEFAULT NULL COMMENT '其他国外借款利息',
  `category_debt_repayment` varchar(64) DEFAULT NULL COMMENT '8、债务还本支出',
  `domestic_debt_repayment` varchar(64) DEFAULT NULL COMMENT '国内债务还本',
  `foreign_debt_repayment` varchar(64) DEFAULT NULL COMMENT '国外债务还本',
  `category_capital_construction` varchar(64) DEFAULT NULL COMMENT '9、基本建设支出',
  `building_acquisition` varchar(64) DEFAULT NULL COMMENT '房屋建筑物购建',
  `office_equipment_purchases` varchar(64) DEFAULT NULL COMMENT '办公设备购置',
  `special_equipment_purchases` varchar(64) DEFAULT NULL COMMENT '专用设备购置',
  `vehicle_purchases` varchar(64) DEFAULT NULL COMMENT '交通工具购置',
  `infrastructure_construction` varchar(64) DEFAULT NULL COMMENT '基础设施建设',
  `major_renovations` varchar(64) DEFAULT NULL COMMENT '大型修缮',
  `it_network_construction` varchar(64) DEFAULT NULL COMMENT '信息网络购建',
  `materials_reserves` varchar(64) DEFAULT NULL COMMENT '物资储备',
  `other_capital_construction` varchar(64) DEFAULT NULL COMMENT '其他基本建设支出',
  `category_other_capital_expenditures` varchar(64) DEFAULT NULL COMMENT '10、其他资本性支出',
  `building_acquisition_1` varchar(64) DEFAULT NULL COMMENT '房屋建筑物购建1',
  `office_equipment_purchases_1` varchar(64) DEFAULT NULL COMMENT '办公设备购置1',
  `special_equipment_purchases_1` varchar(64) DEFAULT NULL COMMENT '专用设备购置1',
  `vehicle_purchases_1` varchar(64) DEFAULT NULL COMMENT '交通工具购置1',
  `infrastructure_construction_1` varchar(64) DEFAULT NULL COMMENT '基础设施建设1',
  `major_renovations_1` varchar(64) DEFAULT NULL COMMENT '大型修缮1',
  `it_network_construction_1` varchar(64) DEFAULT NULL COMMENT '信息网络购建1',
  `materials_reserves_1` varchar(64) DEFAULT NULL COMMENT '物资储备1',
  `other_capital_expenditures_1` varchar(64) DEFAULT NULL COMMENT '其他资本性支出1',
  `category_loans_and_equity` varchar(64) DEFAULT NULL COMMENT '11、贷款转贷及产权参股',
  `domestic_loans` varchar(64) DEFAULT NULL COMMENT '国内贷款',
  `foreign_loans` varchar(64) DEFAULT NULL COMMENT '国外贷款',
  `domestic_relending` varchar(64) DEFAULT NULL COMMENT '国内转贷',
  `foreign_relending` varchar(64) DEFAULT NULL COMMENT '国外转贷',
  `equity_participation` varchar(64) DEFAULT NULL COMMENT '产权参股',
  `other_loans_and_equity` varchar(64) DEFAULT NULL COMMENT '其他贷款转贷及产权参股支出',
  `other_expenditures` varchar(64) DEFAULT NULL COMMENT '12、其他支出',
  `created_at` datetime NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_qy_cashflow_id` (`id`),
  KEY `ix_qy_cashflow_com_id` (`com_id`),
  KEY `ix_qy_cashflow_user_id` (`user_id`),
  KEY `ix_qy_cashflow_year` (`year`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `qy_income`
--

DROP TABLE IF EXISTS `qy_income`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `qy_income` (
  `id` int NOT NULL AUTO_INCREMENT,
  `com_id` varchar(50) DEFAULT NULL COMMENT '统一社会信用代码',
  `year` varchar(20) DEFAULT NULL COMMENT '年度',
  `end_type` varchar(10) DEFAULT NULL COMMENT '报告期类型',
  `user_id` varchar(20) DEFAULT NULL COMMENT '用户id',
  `status` varchar(2) DEFAULT NULL COMMENT '数据状态：0、未验证未生效，1、已验证已生效',
  `updated_by` varchar(100) DEFAULT NULL COMMENT '更新人',
  `report_time` varchar(20) DEFAULT NULL COMMENT '报表生成日期',
  `is_consolidated_statements` varchar(20) NOT NULL COMMENT '是否合并报表',
  `category_revenue_items` varchar(64) DEFAULT NULL COMMENT '收入项目',
  `institutional_revenue` varchar(64) DEFAULT NULL COMMENT '事业收入',
  `fiscal_subsidy_revenue` varchar(64) DEFAULT NULL COMMENT '财政补助收入',
  `superior_subsidy_revenue` varchar(64) DEFAULT NULL COMMENT '上级补助收入',
  `affiliated_unit_contributions` varchar(64) DEFAULT NULL COMMENT '附属单位缴款',
  `operating_revenue` varchar(64) DEFAULT NULL COMMENT '经营收入',
  `special_appropriations_received` varchar(64) DEFAULT NULL COMMENT '拨入专款',
  `investment_income` varchar(64) DEFAULT NULL COMMENT '投资收益',
  `donation_income` varchar(64) DEFAULT NULL COMMENT '捐赠收入',
  `interest_income` varchar(64) DEFAULT NULL COMMENT '利息收入',
  `rental_income` varchar(64) DEFAULT NULL COMMENT '租金收入',
  `other_income` varchar(64) DEFAULT NULL COMMENT '其他收入',
  `total_revenue` varchar(64) DEFAULT NULL COMMENT '收入总计',
  `category_expenditure_items` varchar(64) DEFAULT NULL COMMENT '支出项目',
  `institutional_expenditure` varchar(64) DEFAULT NULL COMMENT '事业支出',
  `appropriations_transferred_out` varchar(64) DEFAULT NULL COMMENT '拨出经费',
  `payment_to_superior` varchar(64) DEFAULT NULL COMMENT '上缴上级支出',
  `subsidy_to_affiliated_units` varchar(64) DEFAULT NULL COMMENT '对附属单位补助',
  `operating_expenditure` varchar(64) DEFAULT NULL COMMENT '经营支出',
  `sales_tax` varchar(64) DEFAULT NULL COMMENT '销售税金',
  `transfer_self_raised_construction_funds` varchar(64) DEFAULT NULL COMMENT '结转自筹基建',
  `unit_management_expenses` varchar(64) DEFAULT NULL COMMENT '单位管理费用',
  `asset_disposal_expenses` varchar(64) DEFAULT NULL COMMENT '资产处置费用',
  `income_tax_expense` varchar(64) DEFAULT NULL COMMENT '所得税支出',
  `special_appropriations_transferred_out` varchar(64) DEFAULT NULL COMMENT '拨出专款',
  `special_fund_expenditure` varchar(64) DEFAULT NULL COMMENT '专款支出',
  `other_expenditures` varchar(64) DEFAULT NULL COMMENT '其他支出',
  `total_expenditure` varchar(64) DEFAULT NULL COMMENT '支出总计',
  `category_balance_items` varchar(64) DEFAULT NULL COMMENT '结余项目',
  `institutional_balance` varchar(64) DEFAULT NULL COMMENT '事业结余',
  `operating_balance` varchar(64) DEFAULT NULL COMMENT '经营结余',
  `other_balance_items` varchar(64) DEFAULT NULL COMMENT '其他结余项目',
  `prior_year_operating_loss` varchar(64) DEFAULT NULL COMMENT '以前年度经营亏损（-）',
  `revenue_expenditure_balance` varchar(64) DEFAULT NULL COMMENT '收支结余',
  `balance_distribution` varchar(64) DEFAULT NULL COMMENT '结余分配',
  `payable_income_tax` varchar(64) DEFAULT NULL COMMENT '1.应交所得税',
  `withdrawal_special_fund` varchar(64) DEFAULT NULL COMMENT '2.提取专用基金',
  `transfer_to_institutional_fund` varchar(64) DEFAULT NULL COMMENT '3.转入事业基金',
  `other_distributions` varchar(64) DEFAULT NULL COMMENT '4.其他',
  `created_at` datetime NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_qy_income_id` (`id`),
  KEY `ix_qy_income_com_id` (`com_id`),
  KEY `ix_qy_income_user_id` (`user_id`),
  KEY `ix_qy_income_year` (`year`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `rbac_permissions`
--

DROP TABLE IF EXISTS `rbac_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `rbac_permissions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL COMMENT '权限名称',
  `code` varchar(50) NOT NULL COMMENT '权限代码',
  `description` text COMMENT '权限描述',
  `resource_type` enum('knowledgebase','document','team','user','system') NOT NULL COMMENT '资源类型',
  `permission_type` enum('read','write','delete','admin','share','export') NOT NULL COMMENT '权限类型',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `code` (`code`),
  KEY `idx_resource_type` (`resource_type`),
  KEY `idx_permission_type` (`permission_type`),
  KEY `idx_code` (`code`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='RBAC权限表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `rbac_resource_permissions`
--

DROP TABLE IF EXISTS `rbac_resource_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `rbac_resource_permissions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `resource_type` enum('knowledgebase','document','team','user','system') NOT NULL COMMENT '资源类型',
  `resource_id` varchar(50) NOT NULL COMMENT '资源ID',
  `user_id` varchar(50) NOT NULL COMMENT '用户ID',
  `permission_type` enum('read','write','delete','admin','share','export') NOT NULL COMMENT '权限类型',
  `granted_by` varchar(50) DEFAULT NULL COMMENT '授权人',
  `granted_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '授权时间',
  `expires_at` timestamp NULL DEFAULT NULL COMMENT '过期时间',
  `is_active` tinyint(1) DEFAULT '1' COMMENT '是否有效',
  `tenant_id` varchar(50) DEFAULT NULL COMMENT '租户ID',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_resource` (`resource_type`,`resource_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_permission_type` (`permission_type`),
  KEY `idx_tenant_id` (`tenant_id`),
  KEY `idx_active_expires` (`is_active`,`expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='RBAC资源权限表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `rbac_role_permissions`
--

DROP TABLE IF EXISTS `rbac_role_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `rbac_role_permissions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `role_id` int NOT NULL COMMENT '角色ID',
  `permission_id` int NOT NULL COMMENT '权限ID',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_permission` (`role_id`,`permission_id`),
  KEY `permission_id` (`permission_id`),
  CONSTRAINT `rbac_role_permissions_ibfk_1` FOREIGN KEY (`role_id`) REFERENCES `rbac_roles` (`id`) ON DELETE CASCADE,
  CONSTRAINT `rbac_role_permissions_ibfk_2` FOREIGN KEY (`permission_id`) REFERENCES `rbac_permissions` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=33 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='RBAC角色权限关联表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `rbac_roles`
--

DROP TABLE IF EXISTS `rbac_roles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `rbac_roles` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL COMMENT '角色名称',
  `code` varchar(50) NOT NULL COMMENT '角色代码',
  `description` text COMMENT '角色描述',
  `role_type` enum('super_admin','admin','editor','viewer','user') NOT NULL COMMENT '角色类型',
  `is_system` tinyint(1) DEFAULT '0' COMMENT '是否为系统角色',
  `tenant_id` varchar(50) DEFAULT NULL COMMENT '租户ID',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code_tenant` (`code`,`tenant_id`),
  KEY `idx_role_type` (`role_type`),
  KEY `idx_tenant_id` (`tenant_id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='RBAC角色表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `rbac_team_roles`
--

DROP TABLE IF EXISTS `rbac_team_roles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `rbac_team_roles` (
  `id` varchar(32) NOT NULL COMMENT '主键ID',
  `team_id` varchar(32) NOT NULL COMMENT '团队ID',
  `role_code` varchar(50) NOT NULL COMMENT '角色代码',
  `resource_type` enum('knowledgebase','document','team','user','system') DEFAULT NULL COMMENT '资源类型',
  `resource_id` varchar(50) DEFAULT NULL COMMENT '资源ID',
  `tenant_id` varchar(50) NOT NULL DEFAULT 'default' COMMENT '租户ID',
  `granted_by` varchar(50) DEFAULT NULL COMMENT '授权人',
  `granted_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '授权时间',
  `expires_at` timestamp NULL DEFAULT NULL COMMENT '过期时间',
  `is_active` tinyint(1) DEFAULT '1' COMMENT '是否有效',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_team_id` (`team_id`),
  KEY `idx_role_code` (`role_code`),
  KEY `idx_resource` (`resource_type`,`resource_id`),
  KEY `idx_tenant_id` (`tenant_id`),
  KEY `idx_active_expires` (`is_active`,`expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='RBAC团队角色关联表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `rbac_user_roles`
--

DROP TABLE IF EXISTS `rbac_user_roles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `rbac_user_roles` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` varchar(50) NOT NULL COMMENT '用户ID',
  `role_id` int NOT NULL COMMENT '角色ID',
  `tenant_id` varchar(50) DEFAULT NULL COMMENT '租户ID',
  `resource_type` enum('knowledgebase','document','team','user','system') DEFAULT NULL COMMENT '资源类型',
  `resource_id` varchar(50) DEFAULT NULL COMMENT '资源ID',
  `granted_by` varchar(50) DEFAULT NULL COMMENT '授权人',
  `granted_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '授权时间',
  `expires_at` timestamp NULL DEFAULT NULL COMMENT '过期时间',
  `is_active` tinyint(1) DEFAULT '1' COMMENT '是否有效',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_role_id` (`role_id`),
  KEY `idx_tenant_id` (`tenant_id`),
  KEY `idx_resource` (`resource_type`,`resource_id`),
  KEY `idx_active_expires` (`is_active`,`expires_at`),
  CONSTRAINT `rbac_user_roles_ibfk_1` FOREIGN KEY (`role_id`) REFERENCES `rbac_roles` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='RBAC用户角色关联表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `realtime_interface`
--

DROP TABLE IF EXISTS `realtime_interface`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `realtime_interface` (
  `id` varchar(36) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `tenant_id` varchar(32) NOT NULL,
  `name_cn` varchar(255) NOT NULL,
  `name_en` varchar(255) NOT NULL,
  `protocol` varchar(32) NOT NULL,
  `is_enabled` varchar(1) NOT NULL,
  `request_method` varchar(16) NOT NULL,
  `message_format` varchar(32) NOT NULL,
  `message_header` text,
  `cache_expiry_days` int NOT NULL,
  `cache_type` varchar(32) DEFAULT NULL,
  `cache_table` varchar(128) DEFAULT NULL,
  `cache_key_template` text,
  `connection_type` varchar(32) NOT NULL,
  `connection_address` text NOT NULL,
  `description` text,
  `category` varchar(128) NOT NULL,
  `is_mock` varchar(1) NOT NULL,
  `created_by` varchar(32) NOT NULL,
  `status` varchar(1) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `realtimeinterface_tenant_id_name_en` (`tenant_id`,`name_en`),
  KEY `realtimeinterface_create_time` (`create_time`),
  KEY `realtimeinterface_create_date` (`create_date`),
  KEY `realtimeinterface_update_time` (`update_time`),
  KEY `realtimeinterface_update_date` (`update_date`),
  KEY `realtimeinterface_tenant_id` (`tenant_id`),
  KEY `realtimeinterface_name_cn` (`name_cn`),
  KEY `realtimeinterface_name_en` (`name_en`),
  KEY `realtimeinterface_protocol` (`protocol`),
  KEY `realtimeinterface_request_method` (`request_method`),
  KEY `realtimeinterface_category` (`category`),
  KEY `realtimeinterface_created_by` (`created_by`),
  KEY `realtimeinterface_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `report_result_info`
--

DROP TABLE IF EXISTS `report_result_info`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `report_result_info` (
  `id` int NOT NULL AUTO_INCREMENT,
  `task_id` varchar(255) DEFAULT NULL COMMENT '任务ID',
  `com_name` varchar(255) DEFAULT NULL COMMENT '公司全称',
  `com_id` varchar(50) DEFAULT NULL COMMENT '统一社会信用代码',
  `report_type` varchar(100) DEFAULT NULL COMMENT '报表类型',
  `cust_type` varchar(100) DEFAULT NULL COMMENT '客户类型',
  `indicator_en_name` varchar(255) DEFAULT NULL COMMENT '字段名称',
  `indicator_cn_name` varchar(255) DEFAULT NULL COMMENT '中文字段名称',
  `indicator_values` varchar(255) DEFAULT NULL COMMENT '字段值',
  `indicator_unit` varchar(255) DEFAULT NULL COMMENT '字段单位',
  `created_by` varchar(100) DEFAULT NULL COMMENT '创建人',
  `updated_by` varchar(100) DEFAULT NULL COMMENT '更新人',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `created_at` datetime NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_report_result_info_id` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `search`
--

DROP TABLE IF EXISTS `search`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `search` (
  `id` varchar(32) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `avatar` text,
  `tenant_id` varchar(32) NOT NULL,
  `name` varchar(128) NOT NULL,
  `description` text,
  `created_by` varchar(32) NOT NULL,
  `search_config` longtext NOT NULL,
  `status` varchar(1) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `search_create_time` (`create_time`),
  KEY `search_create_date` (`create_date`),
  KEY `search_update_time` (`update_time`),
  KEY `search_update_date` (`update_date`),
  KEY `search_tenant_id` (`tenant_id`),
  KEY `search_name` (`name`),
  KEY `search_created_by` (`created_by`),
  KEY `search_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sync_logs`
--

DROP TABLE IF EXISTS `sync_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sync_logs` (
  `id` varchar(32) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `connector_id` varchar(32) NOT NULL,
  `status` varchar(128) NOT NULL,
  `from_beginning` varchar(1) DEFAULT NULL,
  `new_docs_indexed` int NOT NULL,
  `total_docs_indexed` int NOT NULL,
  `docs_removed_from_index` int NOT NULL,
  `error_msg` text NOT NULL,
  `error_count` int NOT NULL,
  `full_exception_trace` text,
  `time_started` datetime DEFAULT NULL,
  `poll_range_start` varchar(255) DEFAULT NULL,
  `poll_range_end` varchar(255) DEFAULT NULL,
  `kb_id` varchar(32) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `synclogs_create_time` (`create_time`),
  KEY `synclogs_create_date` (`create_date`),
  KEY `synclogs_update_time` (`update_time`),
  KEY `synclogs_update_date` (`update_date`),
  KEY `synclogs_connector_id` (`connector_id`),
  KEY `synclogs_status` (`status`),
  KEY `synclogs_time_started` (`time_started`),
  KEY `synclogs_poll_range_start` (`poll_range_start`),
  KEY `synclogs_poll_range_end` (`poll_range_end`),
  KEY `synclogs_kb_id` (`kb_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_collect`
--

DROP TABLE IF EXISTS `sys_collect`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sys_collect` (
  `id` varchar(128) NOT NULL COMMENT 'id',
  `com_id` varchar(128) NOT NULL COMMENT '统一社会信用',
  `user_id` varchar(128) NOT NULL COMMENT '创建人id',
  `com_name` varchar(256) DEFAULT NULL COMMENT '公司全称',
  `ts_code` varchar(128) DEFAULT NULL COMMENT '股票代码',
  `exchange` varchar(128) DEFAULT NULL COMMENT '交易所代码',
  `chairman` varchar(128) DEFAULT NULL COMMENT '法人代表',
  `manager` varchar(128) DEFAULT NULL COMMENT '总经理',
  `secretary` varchar(128) DEFAULT NULL COMMENT '董秘',
  `province` varchar(128) DEFAULT NULL COMMENT '所在省份',
  `city` varchar(128) DEFAULT NULL COMMENT '所在城市',
  `website` varchar(256) DEFAULT NULL COMMENT '公司主页',
  `email` varchar(256) DEFAULT NULL COMMENT '电子邮件',
  `created_at` datetime NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_sys_collect_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='收藏列表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_config`
--

DROP TABLE IF EXISTS `sys_config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sys_config` (
  `config_id` int NOT NULL AUTO_INCREMENT COMMENT '参数主键',
  `config_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '参数名称',
  `config_key` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '参数键名',
  `config_value` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '参数键值',
  `config_type` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'N' COMMENT '系统内置（Y是 N否）',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`config_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=100 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='参数配置表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_dept`
--

DROP TABLE IF EXISTS `sys_dept`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sys_dept` (
  `dept_id` bigint NOT NULL AUTO_INCREMENT COMMENT '部门id',
  `parent_id` bigint DEFAULT '0' COMMENT '父部门id',
  `ancestors` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '祖级列表',
  `dept_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '部门名称',
  `order_num` int DEFAULT '0' COMMENT '显示顺序',
  `leader` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '负责人',
  `phone` varchar(11) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '联系电话',
  `email` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '邮箱',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '0' COMMENT '部门状态（0正常 1停用）',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '0' COMMENT '删除标志（0代表存在 2代表删除）',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`dept_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=204 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='部门表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_dict_data`
--

DROP TABLE IF EXISTS `sys_dict_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sys_dict_data` (
  `dict_code` bigint NOT NULL AUTO_INCREMENT COMMENT '字典编码',
  `dict_sort` int DEFAULT '0' COMMENT '字典排序',
  `dict_label` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '字典标签',
  `dict_value` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '字典键值',
  `dict_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '字典类型',
  `css_class` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '样式属性（其他样式扩展）',
  `list_class` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '表格回显样式',
  `is_default` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'N' COMMENT '是否默认（Y是 N否）',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '0' COMMENT '状态（0正常 1停用）',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '备注',
  `created_at` datetime DEFAULT NULL,
  `updated_at` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`dict_code`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2046 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='字典数据表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_dict_type`
--

DROP TABLE IF EXISTS `sys_dict_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sys_dict_type` (
  `dict_id` bigint NOT NULL AUTO_INCREMENT COMMENT '字典主键',
  `dict_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '字典名称',
  `dict_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '字典类型',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '0' COMMENT '状态（0正常 1停用）',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`dict_id`) USING BTREE,
  UNIQUE KEY `dict_type` (`dict_type`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1009 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='字典类型表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_job`
--

DROP TABLE IF EXISTS `sys_job`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sys_job` (
  `job_id` bigint NOT NULL AUTO_INCREMENT COMMENT '任务ID',
  `job_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '' COMMENT '任务名称',
  `job_group` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT 'DEFAULT' COMMENT '任务组名',
  `invoke_target` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '调用目标字符串',
  `cron_expression` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT 'cron执行表达式',
  `misfire_policy` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '3' COMMENT '计划执行错误策略（1立即执行 2执行一次 3放弃执行）',
  `concurrent` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '1' COMMENT '是否并发执行（0允许 1禁止）',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '0' COMMENT '状态（0正常 1暂停）',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '备注信息',
  PRIMARY KEY (`job_id`,`job_name`,`job_group`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=100 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='定时任务调度表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_job_log`
--

DROP TABLE IF EXISTS `sys_job_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sys_job_log` (
  `job_log_id` bigint NOT NULL AUTO_INCREMENT COMMENT '任务日志ID',
  `job_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '任务名称',
  `job_group` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '任务组名',
  `invoke_target` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '调用目标字符串',
  `job_message` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '日志信息',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '0' COMMENT '执行状态（0正常 1失败）',
  `exception_info` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '异常信息',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`job_log_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='定时任务调度日志表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_logininfor`
--

DROP TABLE IF EXISTS `sys_logininfor`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sys_logininfor` (
  `info_id` bigint NOT NULL AUTO_INCREMENT COMMENT '访问ID',
  `user_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '用户账号',
  `ipaddr` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '登录IP地址',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '0' COMMENT '登录状态（0成功 1失败）',
  `msg` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '提示信息',
  `access_time` datetime DEFAULT NULL COMMENT '访问时间',
  PRIMARY KEY (`info_id`) USING BTREE,
  KEY `idx_sys_logininfor_s` (`status`) USING BTREE,
  KEY `idx_sys_logininfor_lt` (`access_time`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1717 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='系统访问记录';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_menu`
--

DROP TABLE IF EXISTS `sys_menu`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sys_menu` (
  `menu_id` bigint NOT NULL AUTO_INCREMENT COMMENT '菜单ID',
  `menu_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '菜单名称',
  `parent_id` bigint DEFAULT '0' COMMENT '父菜单ID',
  `order_num` int DEFAULT '0' COMMENT '显示顺序',
  `path` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '路由地址',
  `component` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '组件路径',
  `query` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '路由参数',
  `route_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '路由名称',
  `is_frame` int DEFAULT '1' COMMENT '是否为外链（0是 1否）',
  `is_cache` int DEFAULT '0' COMMENT '是否缓存（0缓存 1不缓存）',
  `menu_type` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '菜单类型（M目录 C菜单 F按钮）',
  `visible` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '0' COMMENT '菜单状态（0显示 1隐藏）',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '0' COMMENT '菜单状态（0正常 1停用）',
  `perms` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '权限标识',
  `icon` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '#' COMMENT '菜单图标',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '备注',
  `menu_category` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '菜单分类（1：应用菜单，2：后台菜单）',
  PRIMARY KEY (`menu_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2038 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='菜单权限表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_notice`
--

DROP TABLE IF EXISTS `sys_notice`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sys_notice` (
  `notice_id` int NOT NULL AUTO_INCREMENT COMMENT '公告ID',
  `notice_title` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '公告标题',
  `notice_type` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '公告类型（1通知 2公告）',
  `notice_content` longblob COMMENT '公告内容',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '0' COMMENT '公告状态（0正常 1关闭）',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`notice_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='通知公告表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_oper_log`
--

DROP TABLE IF EXISTS `sys_oper_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sys_oper_log` (
  `oper_id` bigint NOT NULL AUTO_INCREMENT COMMENT '日志主键',
  `title` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '模块标题',
  `business_type` int DEFAULT '0' COMMENT '业务类型（0其它 1新增 2修改 3删除）',
  `method` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '方法名称',
  `request_method` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '请求方式',
  `operator_type` int DEFAULT '0' COMMENT '操作类别（0其它 1后台用户 2手机端用户）',
  `oper_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '操作人员',
  `dept_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '部门名称',
  `oper_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '请求URL',
  `oper_ip` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '主机地址',
  `oper_location` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '操作地点',
  `oper_param` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '请求参数',
  `json_result` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '返回参数',
  `status` int DEFAULT '0' COMMENT '操作状态（0正常 1异常）',
  `error_msg` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '错误消息',
  `oper_time` datetime DEFAULT NULL COMMENT '操作时间',
  `cost_time` bigint DEFAULT '0' COMMENT '消耗时间',
  PRIMARY KEY (`oper_id`) USING BTREE,
  KEY `idx_sys_oper_log_bt` (`business_type`) USING BTREE,
  KEY `idx_sys_oper_log_s` (`status`) USING BTREE,
  KEY `idx_sys_oper_log_ot` (`oper_time`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=500 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='操作日志记录';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_post`
--

DROP TABLE IF EXISTS `sys_post`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sys_post` (
  `post_id` bigint NOT NULL AUTO_INCREMENT COMMENT '岗位ID',
  `post_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '岗位编码',
  `post_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '岗位名称',
  `post_sort` int NOT NULL COMMENT '显示顺序',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '状态（0正常 1停用）',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`post_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='岗位信息表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_role`
--

DROP TABLE IF EXISTS `sys_role`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sys_role` (
  `role_id` bigint NOT NULL AUTO_INCREMENT COMMENT '角色ID',
  `role_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '角色名称',
  `role_key` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '角色权限字符串',
  `role_sort` int NOT NULL COMMENT '显示顺序',
  `data_scope` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '1' COMMENT '数据范围（1：全部数据权限 2：自定数据权限 3：本部门数据权限 4：本部门及以下数据权限）',
  `menu_check_strictly` tinyint(1) DEFAULT '1' COMMENT '菜单树选择项是否关联显示',
  `dept_check_strictly` tinyint(1) DEFAULT '1' COMMENT '部门树选择项是否关联显示',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '角色状态（0正常 1停用）',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '0' COMMENT '删除标志（0代表存在 2代表删除）',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`role_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=101 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='角色信息表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_role_dept`
--

DROP TABLE IF EXISTS `sys_role_dept`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sys_role_dept` (
  `role_id` bigint NOT NULL COMMENT '角色ID',
  `dept_id` bigint NOT NULL COMMENT '部门ID',
  PRIMARY KEY (`role_id`,`dept_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='角色和部门关联表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_role_menu`
--

DROP TABLE IF EXISTS `sys_role_menu`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sys_role_menu` (
  `role_id` bigint NOT NULL COMMENT '角色ID',
  `menu_id` bigint NOT NULL COMMENT '菜单ID',
  PRIMARY KEY (`role_id`,`menu_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='角色和菜单关联表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_user`
--

DROP TABLE IF EXISTS `sys_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sys_user` (
  `user_id` varchar(64) NOT NULL COMMENT '用户ID',
  `dept_id` bigint DEFAULT NULL COMMENT '部门ID',
  `user_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '用户账号',
  `nick_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '用户昵称',
  `user_type` varchar(2) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '00' COMMENT '用户类型（00系统用户）',
  `email` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '用户邮箱',
  `phonenumber` varchar(11) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '手机号码',
  `sex` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '0' COMMENT '用户性别（0男 1女 2未知）',
  `avatar` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '头像地址',
  `password` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '密码',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '0' COMMENT '账号状态（0正常 1停用）',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '0' COMMENT '删除标志（0代表存在 2代表删除）',
  `login_ip` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '最后登录IP',
  `login_date` datetime DEFAULT NULL COMMENT '最后登录时间',
  `pwd_update_date` datetime DEFAULT NULL COMMENT '密码最后更新时间',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`user_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='用户信息表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_user_post`
--

DROP TABLE IF EXISTS `sys_user_post`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sys_user_post` (
  `user_id` varchar(32) NOT NULL COMMENT '用户ID',
  `post_id` bigint NOT NULL COMMENT '岗位ID',
  PRIMARY KEY (`user_id`,`post_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='用户与岗位关联表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_user_role`
--

DROP TABLE IF EXISTS `sys_user_role`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sys_user_role` (
  `user_id` varchar(32) NOT NULL COMMENT '用户ID',
  `role_id` bigint NOT NULL COMMENT '角色ID',
  PRIMARY KEY (`user_id`,`role_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='用户和角色关联表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_users`
--

DROP TABLE IF EXISTS `sys_users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sys_users` (
  `user_id` varchar(128) NOT NULL COMMENT '用户id',
  `phone` varchar(11) DEFAULT NULL COMMENT '手机',
  `username` varchar(128) DEFAULT NULL COMMENT '用户名',
  `hashed_password` varchar(128) DEFAULT NULL COMMENT '密码',
  `sex` varchar(128) DEFAULT NULL COMMENT '性别',
  `email` varchar(128) DEFAULT NULL COMMENT '邮箱',
  `language` varchar(128) DEFAULT NULL COMMENT '语言',
  `image` varchar(256) DEFAULT NULL COMMENT '头像',
  `role` enum('guest','user','admin') DEFAULT NULL COMMENT '角色',
  `created_at` datetime NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `user_id` (`user_id`),
  UNIQUE KEY `ix_sys_users_phone` (`phone`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户信息';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `system_settings`
--

DROP TABLE IF EXISTS `system_settings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `system_settings` (
  `name` varchar(128) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `source` varchar(32) NOT NULL,
  `data_type` varchar(32) NOT NULL,
  `value` varchar(1024) NOT NULL,
  PRIMARY KEY (`name`),
  KEY `systemsettings_create_time` (`create_time`),
  KEY `systemsettings_create_date` (`create_date`),
  KEY `systemsettings_update_time` (`update_time`),
  KEY `systemsettings_update_date` (`update_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `t_glossary`
--

DROP TABLE IF EXISTS `t_glossary`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `t_glossary` (
  `id` char(32) NOT NULL,
  `source_subject` varchar(500) DEFAULT NULL COMMENT '原文科目',
  `target_subject` varchar(500) DEFAULT NULL COMMENT '目标科目',
  `report_type` varchar(3) NOT NULL COMMENT '报表类型（finance_classify 字典值）',
  `cust_type` varchar(3) NOT NULL COMMENT '客户类型（cust_type 字典值）',
  `create_at` datetime NOT NULL COMMENT '创建时间',
  `update_at` datetime DEFAULT NULL COMMENT '更新时间',
  `create_user` varchar(64) DEFAULT NULL COMMENT '创建人',
  `update_user` varchar(64) DEFAULT NULL COMMENT '更新人',
  PRIMARY KEY (`id`),
  KEY `ix_t_glossary_id` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `t_report_base_info`
--

DROP TABLE IF EXISTS `t_report_base_info`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `t_report_base_info` (
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0' COMMENT '软删除标记：0-未删除、1-已删除',
  `report_id` varchar(32) NOT NULL COMMENT '报表唯一ID',
  `com_id` varchar(32) NOT NULL COMMENT '客户ID/企业统一社会信用代码',
  `com_name` varchar(128) NOT NULL COMMENT '客户名称/企业名称',
  `user_id` varchar(32) NOT NULL COMMENT '创建人用户ID',
  `report_type` varchar(16) NOT NULL COMMENT '报表类型：01-年度财报、02-季度财报、03-月度财报、04-专项报表',
  `report_year` varchar(4) NOT NULL COMMENT '报表年份',
  `report_period` varchar(16) DEFAULT NULL COMMENT '报表期间：Q1、H1、12月等',
  `report_scope` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '报表范围：01-单一、02-合并',
  `cust_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '客户类型',
  `status` varchar(16) NOT NULL COMMENT '报表状态：PENDING-待处理、PROCESSING-生成中、SUCCESS-已完成、FAILURE-生成失败、ADJUSTED-已人工调整',
  `template_id` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '关联模板ID',
  `create_user` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '创建人',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_user` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '创建人',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `adjust_remark` varchar(512) DEFAULT NULL COMMENT '人工调整备注',
  `report_end_date` varchar(30) DEFAULT NULL COMMENT '报表截止日期',
  `task_id` varchar(40) DEFAULT NULL COMMENT '标准化任务ID',
  `chunk_bbox` varchar(4000) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '问题返回信息(chunk_id和bbox)',
  `doc_ids` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '问题返回信息(文档ID)',
  PRIMARY KEY (`report_id`),
  KEY `idx_customer` (`com_id`,`report_year`,`report_type`),
  KEY `idx_user` (`user_id`,`created_at`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='报表基本信息主表--科目';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `t_report_check_result`
--

DROP TABLE IF EXISTS `t_report_check_result`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `t_report_check_result` (
  `check_id` varchar(32) NOT NULL COMMENT '校验记录唯一ID',
  `report_id` varchar(32) NOT NULL COMMENT '关联报表ID',
  `mapping_type` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '映射类型01-自定义02-勾稽关系',
  `report_category` varchar(32) DEFAULT NULL COMMENT '报表分类：资产负债表、利润表、现金流量表等',
  `rule_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '勾稽规则编码/指标编号',
  `rule_name` varchar(128) NOT NULL COMMENT '勾稽规则名称',
  `rule_description` varchar(512) DEFAULT NULL COMMENT '规则详细描述',
  `check_result` varchar(16) NOT NULL COMMENT '校验结果：PASS-校验通过、FAIL-校验不通过、SKIP-跳过校验、ADJUSTED-已人工调整',
  `difference_value` decimal(18,2) DEFAULT NULL COMMENT '差异值',
  `difference_rate` varchar(100) DEFAULT NULL COMMENT '差异率',
  `error_msg` text COMMENT '错误说明',
  `threshold_value` decimal(18,2) DEFAULT NULL COMMENT '合理阈值',
  `is_manual_override` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否人工跳过/调整：0-系统校验结果、1-人工修改结果',
  `override_remark` varchar(512) DEFAULT NULL COMMENT '人工调整备注',
  `check_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '校验时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0' COMMENT '软删除标记：0-未删除、1-已删除',
  `created_at` datetime DEFAULT NULL COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  `source_value` decimal(18,2) DEFAULT NULL COMMENT '勾稽/指标原值',
  `unit` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '单位：元、万元、亿元',
  `calculated_value` decimal(18,2) DEFAULT NULL COMMENT '计算值',
  `formula_cn` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '中文公式',
  `task_id` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '勾稽/指标任务ID',
  PRIMARY KEY (`check_id`),
  KEY `idx_report_id` (`report_id`),
  KEY `idx_report_category` (`report_id`,`report_category`),
  KEY `idx_check_result` (`report_id`,`check_result`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='指标/勾稽关系校验结果表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `t_report_detail`
--

DROP TABLE IF EXISTS `t_report_detail`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `t_report_detail` (
  `detail_id` varchar(32) NOT NULL COMMENT '明细唯一ID',
  `report_id` varchar(32) NOT NULL COMMENT '关联报表ID',
  `report_category` varchar(32) NOT NULL COMMENT '报表分类：资产负债表、利润表、现金流量表、所有者权益变动表、附注表',
  `com_id` varchar(32) NOT NULL COMMENT '客户ID/企业统一社会信用代码',
  `item_code` varchar(64) NOT NULL COMMENT '行项目编码（财务标准科目编码）',
  `item_name` varchar(128) NOT NULL COMMENT '行项目名称',
  `item_level` tinyint DEFAULT NULL COMMENT '项目层级：1-一级科目、2-二级明细、3-三级明细',
  `parent_item_code` varchar(64) DEFAULT NULL COMMENT '父级项目编码',
  `current_period_value` decimal(18,2) DEFAULT NULL COMMENT '本期金额0',
  `previous_period_value` decimal(18,2) DEFAULT NULL COMMENT '上期金额',
  `year_begin_value` decimal(18,2) DEFAULT NULL COMMENT '年初余额',
  `unit` varchar(16) NOT NULL DEFAULT '元' COMMENT '数值单位：元、万元、亿元',
  `is_adjusted` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否人工调整：0-系统生成、1-人工修改',
  `adjust_remark` varchar(256) DEFAULT NULL COMMENT '调整备注',
  `template_id` varchar(32) DEFAULT NULL COMMENT '关联模板ID',
  `create_user` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '创建人',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_user` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '创建人',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0' COMMENT '软删除标记：0-未删除、1-已删除',
  `subject_flg` varchar(1) DEFAULT NULL COMMENT '是否科目:1-是 0-否',
  `row_num` varchar(20) DEFAULT NULL COMMENT '目标行数',
  `task_id` varchar(40) DEFAULT NULL COMMENT '标准化任务ID',
  PRIMARY KEY (`detail_id`),
  UNIQUE KEY `t_report_detail_unique` (`report_category`,`report_id`,`item_code`),
  KEY `idx_report_id` (`report_id`),
  KEY `idx_category` (`report_id`,`report_category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='报表分类明细结果表-科目（窄表设计）';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `task`
--

DROP TABLE IF EXISTS `task`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task` (
  `id` varchar(32) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `doc_id` varchar(32) NOT NULL,
  `from_page` int NOT NULL,
  `to_page` int NOT NULL,
  `task_type` varchar(32) NOT NULL,
  `priority` int NOT NULL,
  `begin_at` datetime DEFAULT NULL,
  `process_duration` float NOT NULL,
  `progress` float NOT NULL,
  `progress_msg` text,
  `retry_count` int NOT NULL,
  `digest` text,
  `chunk_ids` longtext,
  PRIMARY KEY (`id`),
  KEY `task_create_time` (`create_time`),
  KEY `task_create_date` (`create_date`),
  KEY `task_update_time` (`update_time`),
  KEY `task_update_date` (`update_date`),
  KEY `task_doc_id` (`doc_id`),
  KEY `task_begin_at` (`begin_at`),
  KEY `task_progress` (`progress`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tenant`
--

DROP TABLE IF EXISTS `tenant`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `tenant` (
  `id` varchar(32) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `name` varchar(100) DEFAULT NULL,
  `public_key` varchar(255) DEFAULT NULL,
  `llm_id` varchar(128) NOT NULL,
  `embd_id` varchar(128) NOT NULL,
  `asr_id` varchar(128) NOT NULL,
  `img2txt_id` varchar(128) NOT NULL,
  `rerank_id` varchar(128) NOT NULL,
  `tts_id` varchar(256) DEFAULT NULL,
  `parser_ids` varchar(256) NOT NULL,
  `credit` int NOT NULL,
  `status` varchar(1) DEFAULT NULL,
  `created_by` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `tenant_create_time` (`create_time`),
  KEY `tenant_create_date` (`create_date`),
  KEY `tenant_update_time` (`update_time`),
  KEY `tenant_update_date` (`update_date`),
  KEY `tenant_name` (`name`),
  KEY `tenant_public_key` (`public_key`),
  KEY `tenant_llm_id` (`llm_id`),
  KEY `tenant_embd_id` (`embd_id`),
  KEY `tenant_asr_id` (`asr_id`),
  KEY `tenant_img2txt_id` (`img2txt_id`),
  KEY `tenant_rerank_id` (`rerank_id`),
  KEY `tenant_tts_id` (`tts_id`),
  KEY `tenant_parser_ids` (`parser_ids`),
  KEY `tenant_credit` (`credit`),
  KEY `tenant_status` (`status`),
  KEY `tenant_created_by` (`created_by`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tenant_langfuse`
--

DROP TABLE IF EXISTS `tenant_langfuse`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `tenant_langfuse` (
  `tenant_id` varchar(32) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `secret_key` varchar(2048) NOT NULL,
  `public_key` varchar(2048) NOT NULL,
  `host` varchar(128) NOT NULL,
  PRIMARY KEY (`tenant_id`),
  KEY `tenantlangfuse_create_time` (`create_time`),
  KEY `tenantlangfuse_create_date` (`create_date`),
  KEY `tenantlangfuse_update_time` (`update_time`),
  KEY `tenantlangfuse_update_date` (`update_date`),
  KEY `tenantlangfuse_secret_key` (`secret_key`(768)),
  KEY `tenantlangfuse_public_key` (`public_key`(768)),
  KEY `tenantlangfuse_host` (`host`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tenant_llm`
--

DROP TABLE IF EXISTS `tenant_llm`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `tenant_llm` (
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `tenant_id` varchar(32) NOT NULL,
  `llm_factory` varchar(128) NOT NULL,
  `model_type` varchar(128) DEFAULT NULL,
  `llm_name` varchar(128) NOT NULL,
  `api_key` text,
  `api_base` varchar(255) DEFAULT NULL,
  `max_tokens` int NOT NULL,
  `used_tokens` int NOT NULL,
  `status` varchar(1) NOT NULL,
  PRIMARY KEY (`tenant_id`,`llm_factory`,`llm_name`),
  KEY `tenantllm_create_time` (`create_time`),
  KEY `tenantllm_create_date` (`create_date`),
  KEY `tenantllm_update_time` (`update_time`),
  KEY `tenantllm_update_date` (`update_date`),
  KEY `tenantllm_tenant_id` (`tenant_id`),
  KEY `tenantllm_llm_factory` (`llm_factory`),
  KEY `tenantllm_model_type` (`model_type`),
  KEY `tenantllm_llm_name` (`llm_name`),
  KEY `tenantllm_max_tokens` (`max_tokens`),
  KEY `tenantllm_used_tokens` (`used_tokens`),
  KEY `tenantllm_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ts_announcement`
--

DROP TABLE IF EXISTS `ts_announcement`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ts_announcement` (
  `id` int NOT NULL AUTO_INCREMENT,
  `com_id` varchar(50) DEFAULT NULL COMMENT '统一社会信用代码',
  `end_type` varchar(20) DEFAULT NULL COMMENT '报告期',
  `year` varchar(20) DEFAULT NULL COMMENT '年度',
  `user_id` varchar(20) DEFAULT NULL COMMENT '用户id',
  `ann_date` varchar(128) DEFAULT NULL COMMENT '公告日期',
  `ts_code` varchar(128) DEFAULT NULL COMMENT '股票代码',
  `name` varchar(256) DEFAULT NULL COMMENT '股票名称',
  `title` varchar(256) DEFAULT NULL COMMENT '公告标题',
  `url` varchar(256) DEFAULT NULL COMMENT '公告链接',
  `path` varchar(256) DEFAULT NULL COMMENT '保存路径',
  `rec_time` varchar(256) DEFAULT NULL COMMENT '公告发布时间',
  `created_at` datetime NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_ts_announcement_user_id` (`user_id`),
  KEY `ix_ts_announcement_ts_code` (`ts_code`),
  KEY `ix_ts_announcement_end_type` (`end_type`),
  KEY `ix_ts_announcement_id` (`id`),
  KEY `ix_ts_announcement_year` (`year`),
  KEY `ix_ts_announcement_com_id` (`com_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='公告信息数据';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ts_balance_sheet`
--

DROP TABLE IF EXISTS `ts_balance_sheet`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ts_balance_sheet` (
  `id` int NOT NULL AUTO_INCREMENT,
  `com_id` varchar(50) DEFAULT NULL COMMENT '统一社会信用代码',
  `year` varchar(20) DEFAULT NULL COMMENT '年度',
  `end_type` varchar(10) DEFAULT NULL COMMENT '报告期类型',
  `user_id` varchar(20) DEFAULT NULL COMMENT '用户id',
  `status` varchar(2) DEFAULT NULL COMMENT '数据状态：0、未验证未生效，1、已验证已生效',
  `updated_by` varchar(100) DEFAULT NULL COMMENT '更新人',
  `report_time` varchar(20) DEFAULT NULL COMMENT '报表生成日期',
  `is_consolidated_statements` varchar(20) NOT NULL COMMENT '是否合并报表',
  `ts_code` varchar(20) DEFAULT NULL COMMENT 'TS股票代码',
  `ann_date` varchar(20) DEFAULT NULL COMMENT '公告日期',
  `f_ann_date` varchar(20) DEFAULT NULL COMMENT '实际公告日期',
  `comp_type` varchar(10) DEFAULT NULL COMMENT '公司类型(1一般工商业2银行3保险4证券)',
  `report_type` varchar(10) DEFAULT NULL COMMENT '报表类型',
  `end_date` varchar(20) DEFAULT NULL COMMENT '报告期',
  `assets` varchar(64) DEFAULT NULL COMMENT '一、资产类',
  `current_assets` varchar(64) DEFAULT NULL COMMENT '流动资产：',
  `cash` varchar(64) DEFAULT NULL COMMENT '货币资金',
  `settlement_fund` varchar(64) DEFAULT NULL COMMENT '结算备付金',
  `loans_to_others` varchar(64) DEFAULT NULL COMMENT '拆出资金',
  `short_term_invest` varchar(64) DEFAULT NULL COMMENT '短期投资',
  `trading_fa` varchar(64) DEFAULT NULL COMMENT '交易性金融资产',
  `derivative_fa` varchar(64) DEFAULT NULL COMMENT '衍生金融资产',
  `notes_receivable` varchar(64) DEFAULT NULL COMMENT '应收票据',
  `accounts_receivable` varchar(64) DEFAULT NULL COMMENT '应收账款',
  `financing_receivable` varchar(64) DEFAULT NULL COMMENT '应收款项融资',
  `subsidy_receivable` varchar(64) DEFAULT NULL COMMENT '应收补贴款',
  `export_tax_receivable` varchar(64) DEFAULT NULL COMMENT '应收出口退税',
  `dividend_receivable` varchar(64) DEFAULT NULL COMMENT '应收股利',
  `interest_receivable` varchar(64) DEFAULT NULL COMMENT '应收利息',
  `other_receivable` varchar(64) DEFAULT NULL COMMENT '其他应收款',
  `prepayment` varchar(64) DEFAULT NULL COMMENT '预付账款',
  `futures_margin` varchar(64) DEFAULT NULL COMMENT '期货保证金',
  `reverse_repurchase` varchar(64) DEFAULT NULL COMMENT '买入返售金融资产',
  `inventory` varchar(64) DEFAULT NULL COMMENT '存货',
  `contract_asset` varchar(64) DEFAULT NULL COMMENT '合同资产',
  `held_for_sale` varchar(64) DEFAULT NULL COMMENT '持有待售资产',
  `current_asset_loss` varchar(64) DEFAULT NULL COMMENT '待处理流动资产损失',
  `prepaid_expenses` varchar(64) DEFAULT NULL COMMENT '待摊费用',
  `other_current_assets` varchar(64) DEFAULT NULL COMMENT '其他流动资产',
  `noncurrent_due_1y` varchar(64) DEFAULT NULL COMMENT '一年内到期的非流动资产',
  `total_current_assets` varchar(64) DEFAULT NULL COMMENT '流动资产合计',
  `noncurrent_assets` varchar(64) DEFAULT NULL COMMENT '非流动资产：',
  `loans_and_advances` varchar(64) DEFAULT NULL COMMENT '发放贷款和垫款',
  `available_for_sale_fa` varchar(64) DEFAULT NULL COMMENT '可供出售金融资产',
  `long_term_receivable` varchar(64) DEFAULT NULL COMMENT '长期应收款',
  `long_term_invest` varchar(64) DEFAULT NULL COMMENT '长期股权投资',
  `other_equity_invest` varchar(64) DEFAULT NULL COMMENT '其他权益工具投资',
  `other_noncurrent_fa` varchar(64) DEFAULT NULL COMMENT '其他非流动金融资产',
  `investment_property` varchar(64) DEFAULT NULL COMMENT '投资性房地产',
  `fixed_assets` varchar(64) DEFAULT NULL COMMENT '固定资产',
  `construction_in_progress` varchar(64) DEFAULT NULL COMMENT '在建工程',
  `construction_materials` varchar(64) DEFAULT NULL COMMENT '工程物资',
  `fixed_assets_disposal` varchar(64) DEFAULT NULL COMMENT '固定资产清理',
  `biological_assets` varchar(64) DEFAULT NULL COMMENT '生产性生物资产',
  `oil_gas_assets` varchar(64) DEFAULT NULL COMMENT '油气资产',
  `right_of_use` varchar(64) DEFAULT NULL COMMENT '使用权资产',
  `intangible_assets` varchar(64) DEFAULT NULL COMMENT '无形资产',
  `development_exp` varchar(64) DEFAULT NULL COMMENT '开发支出',
  `goodwill` varchar(64) DEFAULT NULL COMMENT '商誉',
  `long_term_prepaid` varchar(64) DEFAULT NULL COMMENT '长期待摊费用',
  `deferred_tax_assets` varchar(64) DEFAULT NULL COMMENT '递延所得税资产',
  `other_noncurrent_assets` varchar(64) DEFAULT NULL COMMENT '其他非流动资产',
  `held_to_maturity` varchar(64) DEFAULT NULL COMMENT '持有至到期投资',
  `fixed_asset_loss` varchar(64) DEFAULT NULL COMMENT '待处理固定资产净损失',
  `loans_and_advances_2` varchar(64) DEFAULT NULL COMMENT '发放贷款及垫款',
  `total_noncurrent_assets` varchar(64) DEFAULT NULL COMMENT '非流动资产合计',
  `total_assets` varchar(64) DEFAULT NULL COMMENT '资产合计',
  `liabilities` varchar(64) DEFAULT NULL COMMENT '二、负债类',
  `current_liabilities` varchar(64) DEFAULT NULL COMMENT '流动负债：',
  `short_term_loan` varchar(64) DEFAULT NULL COMMENT '短期借款',
  `central_bank_loan` varchar(64) DEFAULT NULL COMMENT '向中央银行借款',
  `loans_from_others` varchar(64) DEFAULT NULL COMMENT '拆入资金',
  `trading_fl` varchar(64) DEFAULT NULL COMMENT '交易性金融负债',
  `derivative_fl` varchar(64) DEFAULT NULL COMMENT '衍生金融负债',
  `notes_payable` varchar(64) DEFAULT NULL COMMENT '应付票据',
  `accounts_payable` varchar(64) DEFAULT NULL COMMENT '应付账款',
  `advance_from_customers` varchar(64) DEFAULT NULL COMMENT '预收账款',
  `contract_liability` varchar(64) DEFAULT NULL COMMENT '合同负债',
  `repurchase_agreement` varchar(64) DEFAULT NULL COMMENT '卖出回购金融资产款',
  `deposits` varchar(64) DEFAULT NULL COMMENT '吸收存款及同业存放',
  `trading_securities` varchar(64) DEFAULT NULL COMMENT '代理买卖证券款',
  `underwriting_securities` varchar(64) DEFAULT NULL COMMENT '代理承销证券款',
  `employee_benefits_payable` varchar(64) DEFAULT NULL COMMENT '应付职工薪酬',
  `taxes_payable` varchar(64) DEFAULT NULL COMMENT '应交税费',
  `other_payables` varchar(64) DEFAULT NULL COMMENT '其他应付款',
  `interest_payable` varchar(64) DEFAULT NULL COMMENT '其中：应付利息',
  `dividend_payable` varchar(64) DEFAULT NULL COMMENT '应付股利',
  `welfare_payable` varchar(64) DEFAULT NULL COMMENT '应付福利费',
  `profit_payable` varchar(64) DEFAULT NULL COMMENT '应交利润',
  `fees_commissions_payable` varchar(64) DEFAULT NULL COMMENT '应付手续费及佣金',
  `accrued_expenses` varchar(64) DEFAULT NULL COMMENT '预提费用',
  `held_for_sale_liab` varchar(64) DEFAULT NULL COMMENT '持有待售负债',
  `noncurrent_due_1y_liab` varchar(64) DEFAULT NULL COMMENT '一年内到期的非流动负债',
  `other_current_liab` varchar(64) DEFAULT NULL COMMENT '其他流动负债',
  `total_current_liab` varchar(64) DEFAULT NULL COMMENT '流动负债合计',
  `noncurrent_liab` varchar(64) DEFAULT NULL COMMENT '非流动负债：',
  `long_term_loan` varchar(64) DEFAULT NULL COMMENT '长期借款',
  `bonds_payable` varchar(64) DEFAULT NULL COMMENT '应付债券',
  `lease_liability` varchar(64) DEFAULT NULL COMMENT '租赁负债',
  `long_term_payable` varchar(64) DEFAULT NULL COMMENT '长期应付款',
  `long_term_employee_benefits` varchar(64) DEFAULT NULL COMMENT '长期应付职工薪酬',
  `special_payable` varchar(64) DEFAULT NULL COMMENT '专项应付款',
  `estimated_liab` varchar(64) DEFAULT NULL COMMENT '预计负债',
  `deferred_income` varchar(64) DEFAULT NULL COMMENT '递延收益',
  `deferred_tax_liab` varchar(64) DEFAULT NULL COMMENT '递延所得税负债',
  `other_noncurrent_liab` varchar(64) DEFAULT NULL COMMENT '其他非流动负债',
  `total_noncurrent_liab` varchar(64) DEFAULT NULL COMMENT '非流动负债合计',
  `total_liab` varchar(64) DEFAULT NULL COMMENT '负债合计',
  `equity` varchar(64) DEFAULT NULL COMMENT '三、所有者权益（或股东权益）：',
  `share_capital` varchar(64) DEFAULT NULL COMMENT '实收资本（或股本）',
  `other_equity_instruments` varchar(64) DEFAULT NULL COMMENT '其他权益工具',
  `preferred_stock` varchar(64) DEFAULT NULL COMMENT '其中：优先股',
  `perpetual_bond` varchar(64) DEFAULT NULL COMMENT '永续债',
  `capital_reserve` varchar(64) DEFAULT NULL COMMENT '资本公积',
  `treasury_stock` varchar(64) DEFAULT NULL COMMENT '减：库存股',
  `other_comprehensive_income` varchar(64) DEFAULT NULL COMMENT '其他综合收益',
  `special_reserve` varchar(64) DEFAULT NULL COMMENT '专项储备',
  `surplus_reserve` varchar(64) DEFAULT NULL COMMENT '盈余公积',
  `general_risk_reserve` varchar(64) DEFAULT NULL COMMENT '一般风险准备',
  `retained_earnings` varchar(64) DEFAULT NULL COMMENT '未分配利润',
  `foreign_exchange_diff` varchar(64) DEFAULT NULL COMMENT '外币报表折算差额',
  `parent_equity` varchar(64) DEFAULT NULL COMMENT '归属于母公司所有者权益合计',
  `minority_interest` varchar(64) DEFAULT NULL COMMENT '少数股东权益',
  `total_equity` varchar(64) DEFAULT NULL COMMENT '所有者权益（或股东权益）合计',
  `total_liab_equity` varchar(64) DEFAULT NULL COMMENT '负债和所有者权益（或股东权益）总计',
  `update_flag` varchar(1) DEFAULT NULL COMMENT '更新标识',
  `created_at` datetime NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_ts_balance_sheet_ts_code` (`ts_code`),
  KEY `ix_ts_balance_sheet_com_id` (`com_id`),
  KEY `ix_ts_balance_sheet_year` (`year`),
  KEY `ix_ts_balance_sheet_end_date` (`end_date`),
  KEY `ix_ts_balance_sheet_user_id` (`user_id`),
  KEY `ix_ts_balance_sheet_id` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='资产负债表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ts_cashflow`
--

DROP TABLE IF EXISTS `ts_cashflow`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ts_cashflow` (
  `id` int NOT NULL AUTO_INCREMENT,
  `com_id` varchar(50) DEFAULT NULL COMMENT '统一社会信用代码',
  `year` varchar(20) DEFAULT NULL COMMENT '年度',
  `end_type` varchar(10) DEFAULT NULL COMMENT '报告期类型',
  `user_id` varchar(20) DEFAULT NULL COMMENT '用户id',
  `status` varchar(2) DEFAULT NULL COMMENT '数据状态：0、未验证未生效，1、已验证已生效',
  `updated_by` varchar(100) DEFAULT NULL COMMENT '更新人',
  `report_time` varchar(20) DEFAULT NULL COMMENT '报表生成日期',
  `is_consolidated_statements` varchar(20) NOT NULL COMMENT '是否合并报表',
  `ts_code` varchar(20) DEFAULT NULL COMMENT 'TS股票代码',
  `ann_date` varchar(20) DEFAULT NULL COMMENT '公告日期',
  `f_ann_date` varchar(20) DEFAULT NULL COMMENT '实际公告日期',
  `comp_type` varchar(10) DEFAULT NULL COMMENT '公司类型(1一般工商业2银行3保险4证券)',
  `report_type` varchar(10) DEFAULT NULL COMMENT '报表类型',
  `end_date` varchar(20) DEFAULT NULL COMMENT '报告期',
  `operating_cf` varchar(64) DEFAULT NULL COMMENT '一、经营活动产生的现金流量：',
  `cash_from_sales` varchar(64) DEFAULT NULL COMMENT '销售商品、提供劳务收到的现金',
  `net_increase_deposits` varchar(64) DEFAULT NULL COMMENT '客户存款和同业存放款项净增加额',
  `net_increase_central_bank_borrow` varchar(64) DEFAULT NULL COMMENT '向中央银行借款净增加额',
  `net_increase_financial_institution_borrow` varchar(64) DEFAULT NULL COMMENT '向其他金融机构拆入资金净增加额',
  `cash_from_interest_fees` varchar(64) DEFAULT NULL COMMENT '收取利息、手续费及佣金的现金',
  `net_increase_borrowed_funds` varchar(64) DEFAULT NULL COMMENT '拆入资金净增加额',
  `net_increase_repurchase` varchar(64) DEFAULT NULL COMMENT '回购业务资金净增加额',
  `net_cash_from_security_trading` varchar(64) DEFAULT NULL COMMENT '代理买卖证券收到的现金净额',
  `tax_refund_received` varchar(64) DEFAULT NULL COMMENT '收到的税费返还',
  `other_operating_cash_in` varchar(64) DEFAULT NULL COMMENT '收到其他与经营活动有关的现金',
  `total_operating_cash_in` varchar(64) DEFAULT NULL COMMENT '经营活动现金流入小计',
  `cash_for_purchases` varchar(64) DEFAULT NULL COMMENT '购买商品、接受劳务支付的现金',
  `net_increase_loans` varchar(64) DEFAULT NULL COMMENT '客户贷款及垫款净增加额',
  `net_increase_deposits_central_bank` varchar(64) DEFAULT NULL COMMENT '存放中央银行和同业款项净增加额',
  `net_increase_loans_to_others` varchar(64) DEFAULT NULL COMMENT '拆出资金净增加额',
  `cash_for_interest_fees` varchar(64) DEFAULT NULL COMMENT '支付利息、手续费及佣金的现金',
  `cash_for_employees` varchar(64) DEFAULT NULL COMMENT '支付给职工以及为职工支付的现金',
  `cash_for_taxes` varchar(64) DEFAULT NULL COMMENT '支付的各项税费',
  `other_operating_cash_out` varchar(64) DEFAULT NULL COMMENT '支付其他与经营活动有关的现金',
  `total_operating_cash_out` varchar(64) DEFAULT NULL COMMENT '经营活动现金流出小计',
  `net_operating_cf` varchar(64) DEFAULT NULL COMMENT '经营活动产生的现金流量净额',
  `investing_cf` varchar(64) DEFAULT NULL COMMENT '二、投资活动产生的现金流量：',
  `cash_from_investment_recovery` varchar(64) DEFAULT NULL COMMENT '收回投资收到的现金',
  `cash_from_investment_income` varchar(64) DEFAULT NULL COMMENT '取得投资收益收到的现金',
  `cash_from_asset_disposal` varchar(64) DEFAULT NULL COMMENT '处置固定资产、无形资产和其他长期资产收回的现金净额',
  `cash_from_subsidiary_disposal` varchar(64) DEFAULT NULL COMMENT '处置子公司及其他营业单位收到的现金净额',
  `other_investing_cash_in` varchar(64) DEFAULT NULL COMMENT '收到其他与投资活动有关的现金',
  `total_investing_cash_in` varchar(64) DEFAULT NULL COMMENT '投资活动现金流入小计',
  `cash_for_asset_acquisition` varchar(64) DEFAULT NULL COMMENT '购建固定资产、无形资产和其他长期资产支付的现金投资支付的现金',
  `cash_for_investments` varchar(64) DEFAULT NULL COMMENT '投资支付的现金',
  `net_increase_pledged_loans` varchar(64) DEFAULT NULL COMMENT '质押贷款净增加额',
  `cash_for_subsidiary_acquisition` varchar(64) DEFAULT NULL COMMENT '取得子公司及其他营业单位支付的现金净额',
  `other_investing_cash_out` varchar(64) DEFAULT NULL COMMENT '支付其他与投资活动有关的现金',
  `total_investing_cash_out` varchar(64) DEFAULT NULL COMMENT '投资活动现金流出小计',
  `net_investing_cf` varchar(64) DEFAULT NULL COMMENT '投资活动产生的现金流量净额',
  `financing_cf` varchar(64) DEFAULT NULL COMMENT '三、筹资活动产生的现金流量：',
  `cash_from_investment` varchar(64) DEFAULT NULL COMMENT '吸收投资收到的现金',
  `cash_from_borrowing` varchar(64) DEFAULT NULL COMMENT '取得借款收到的现金',
  `other_financing_cash_in` varchar(64) DEFAULT NULL COMMENT '收到其他与筹资活动有关的现金',
  `total_financing_cash_in` varchar(64) DEFAULT NULL COMMENT '筹资活动现金流入小计',
  `cash_for_debt_repayment` varchar(64) DEFAULT NULL COMMENT '偿还债务支付的现金',
  `cash_for_dividends_interest` varchar(64) DEFAULT NULL COMMENT '分配股利、利润或偿付利息支付的现金',
  `other_financing_cash_out` varchar(64) DEFAULT NULL COMMENT '支付其他与筹资活动有关的现金',
  `total_financing_cash_out` varchar(64) DEFAULT NULL COMMENT '筹资活动现金流出小计',
  `net_financing_cf` varchar(64) DEFAULT NULL COMMENT '筹资活动产生的现金流量净额',
  `fx_effect_cash` varchar(64) DEFAULT NULL COMMENT '四、汇率变动对现金及现金等价物的影响',
  `net_cash_increase` varchar(64) DEFAULT NULL COMMENT '五、现金及现金等价物净增加额',
  `beginning_cash_balance` varchar(64) DEFAULT NULL COMMENT '加：期初现金及现金等价物余额',
  `ending_cash_balance` varchar(64) DEFAULT NULL COMMENT '六、期末现金及现金等价物余额',
  `update_flag` varchar(1) DEFAULT NULL COMMENT '更新标志(1最新）',
  `created_at` datetime NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_ts_cashflow_id` (`id`),
  KEY `ix_ts_cashflow_end_date` (`end_date`),
  KEY `ix_ts_cashflow_ts_code` (`ts_code`),
  KEY `ix_ts_cashflow_com_id` (`com_id`),
  KEY `ix_ts_cashflow_user_id` (`user_id`),
  KEY `ix_ts_cashflow_year` (`year`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='现金流量表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ts_company_info`
--

DROP TABLE IF EXISTS `ts_company_info`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ts_company_info` (
  `id` int NOT NULL AUTO_INCREMENT,
  `ts_code` varchar(20) DEFAULT NULL COMMENT '股票代码',
  `com_name` varchar(100) DEFAULT NULL COMMENT '公司全称',
  `com_id` varchar(50) DEFAULT NULL COMMENT '统一社会信用代码',
  `user_id` varchar(20) DEFAULT NULL COMMENT '用户id',
  `exchange` varchar(20) DEFAULT NULL COMMENT '交易所代码',
  `chairman` varchar(50) DEFAULT NULL COMMENT '法人代表',
  `manager` varchar(50) DEFAULT NULL COMMENT '总经理',
  `secretary` varchar(50) DEFAULT NULL COMMENT '董秘',
  `reg_capital` varchar(200) DEFAULT NULL COMMENT '注册资本(万元)',
  `setup_date` varchar(20) DEFAULT NULL COMMENT '注册日期',
  `province` varchar(50) DEFAULT NULL COMMENT '所在省份',
  `city` varchar(50) DEFAULT NULL COMMENT '所在城市',
  `introduction` text COMMENT '公司介绍',
  `website` varchar(200) DEFAULT NULL COMMENT '公司主页',
  `email` varchar(100) DEFAULT NULL COMMENT '电子邮件',
  `office` varchar(200) DEFAULT NULL COMMENT '办公室',
  `employees` varchar(200) DEFAULT NULL COMMENT '员工人数',
  `main_business` text COMMENT '主要业务及产品',
  `business_scope` text COMMENT '经营范围',
  `created_at` datetime NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_ts_company_info_user_id` (`user_id`),
  KEY `ix_ts_company_info_ts_code` (`ts_code`),
  KEY `ix_ts_company_info_com_id` (`com_id`),
  KEY `ix_ts_company_info_id` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='上市公司基本信息';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ts_holder`
--

DROP TABLE IF EXISTS `ts_holder`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ts_holder` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `com_id` varchar(128) DEFAULT NULL COMMENT '统一社会信用代码',
  `year` varchar(20) DEFAULT NULL COMMENT '年度',
  `end_type` varchar(10) DEFAULT NULL COMMENT '报告期类型',
  `user_id` varchar(20) DEFAULT NULL COMMENT '用户id',
  `ts_code` varchar(128) DEFAULT NULL COMMENT 'TS股票代码',
  `ann_date` varchar(128) DEFAULT NULL COMMENT '公告日期',
  `end_date` varchar(128) DEFAULT NULL COMMENT '报告期',
  `holder_name` varchar(128) DEFAULT NULL COMMENT '股东名称',
  `hold_amount` varchar(128) DEFAULT NULL COMMENT '持有数量（股）',
  `hold_ratio` varchar(128) DEFAULT NULL COMMENT '占总股本比例(%)',
  `hold_float_ratio` varchar(128) DEFAULT NULL COMMENT '占流通股本比例(%)',
  `hold_change` varchar(128) DEFAULT NULL COMMENT '持股变动（股）',
  `holder_type` varchar(128) DEFAULT NULL COMMENT '股东性质',
  `created_at` datetime NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_ts_holder_com_id` (`com_id`),
  KEY `ix_ts_holder_id` (`id`),
  KEY `ix_ts_holder_user_id` (`user_id`),
  KEY `ix_ts_holder_ts_code` (`ts_code`),
  KEY `ix_ts_holder_end_date` (`end_date`),
  KEY `ix_ts_holder_end_type` (`end_type`),
  KEY `ix_ts_holder_year` (`year`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股东持股信息表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ts_income`
--

DROP TABLE IF EXISTS `ts_income`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ts_income` (
  `id` int NOT NULL AUTO_INCREMENT,
  `com_id` varchar(50) DEFAULT NULL COMMENT '统一社会信用代码',
  `year` varchar(20) DEFAULT NULL COMMENT '年度',
  `end_type` varchar(10) DEFAULT NULL COMMENT '报告期类型',
  `user_id` varchar(20) DEFAULT NULL COMMENT '用户id',
  `status` varchar(2) DEFAULT NULL COMMENT '数据状态：0、未验证未生效，1、已验证已生效',
  `updated_by` varchar(100) DEFAULT NULL COMMENT '更新人',
  `report_time` varchar(20) DEFAULT NULL COMMENT '报表生成日期',
  `is_consolidated_statements` varchar(20) NOT NULL COMMENT '是否合并报表',
  `ts_code` varchar(20) DEFAULT NULL COMMENT 'TS股票代码',
  `ann_date` varchar(20) DEFAULT NULL COMMENT '公告日期',
  `f_ann_date` varchar(20) DEFAULT NULL COMMENT '实际公告日期',
  `comp_type` varchar(10) DEFAULT NULL COMMENT '公司类型(1一般工商业2银行3保险4证券)',
  `report_type` varchar(10) DEFAULT NULL COMMENT '报表类型',
  `end_date` varchar(20) DEFAULT NULL COMMENT '报告期',
  `total_operating_revenue` varchar(64) DEFAULT NULL COMMENT '一、营业总收入',
  `operating_revenue` varchar(64) DEFAULT NULL COMMENT '其中：营业收入',
  `interest_income` varchar(64) DEFAULT NULL COMMENT '利息收入',
  `fee_commission_income` varchar(64) DEFAULT NULL COMMENT '手续费及佣金收入',
  `total_operating_cost` varchar(64) DEFAULT NULL COMMENT '二、营业总成本',
  `operating_cost` varchar(64) DEFAULT NULL COMMENT '其中：营业成本',
  `interest_expense` varchar(64) DEFAULT NULL COMMENT '利息支出',
  `surrender_payment` varchar(64) DEFAULT NULL COMMENT '退保金',
  `fee_commission_expense` varchar(64) DEFAULT NULL COMMENT '手续费及佣金支出',
  `net_claims_paid` varchar(64) DEFAULT NULL COMMENT '赔付资金净额',
  `taxes_surcharges` varchar(64) DEFAULT NULL COMMENT '税金及附加',
  `asset_impairment_loss` varchar(64) DEFAULT NULL COMMENT '资产减值损失',
  `selling_expenses` varchar(64) DEFAULT NULL COMMENT '销售费用',
  `admin_expenses` varchar(64) DEFAULT NULL COMMENT '管理费用',
  `rd_expenses` varchar(64) DEFAULT NULL COMMENT '研发费用',
  `finance_expenses` varchar(64) DEFAULT NULL COMMENT '财务费用',
  `interest_expense_2` varchar(64) DEFAULT NULL COMMENT '其中：利息费用',
  `other_income` varchar(64) DEFAULT NULL COMMENT '加：其他收益',
  `asset_impairment_loss_2` varchar(64) DEFAULT NULL COMMENT '资产减值损失（损失以“-”号填列）',
  `fair_value_change` varchar(64) DEFAULT NULL COMMENT '公允价值变动收益（损失以“-”号填列）',
  `investment_income` varchar(64) DEFAULT NULL COMMENT '投资收益（损失以“-”号填列）',
  `investment_income_associates` varchar(64) DEFAULT NULL COMMENT '其中：对联营企业和合营企业的投资收益',
  `financial_asset_termination` varchar(64) DEFAULT NULL COMMENT '以摊余成本计量的金融资产终止确认收益',
  `exchange_gain` varchar(64) DEFAULT NULL COMMENT '汇兑收益（损失以“-”号填列）',
  `hedging_gain` varchar(64) DEFAULT NULL COMMENT '净敞口套期收益（损失以“-”号填列）',
  `credit_impairment_loss` varchar(64) DEFAULT NULL COMMENT '信用减值损失（损失以“-”号填列）',
  `asset_disposal_gain` varchar(64) DEFAULT NULL COMMENT '资产处置收益（损失以“-”号填列）',
  `operating_profit` varchar(64) DEFAULT NULL COMMENT '三、营业利润（亏损以“-”号填列）',
  `non_operating_income` varchar(64) DEFAULT NULL COMMENT '加：营业外收入',
  `non_operating_expense` varchar(64) DEFAULT NULL COMMENT '减：营业外支出',
  `total_profit` varchar(64) DEFAULT NULL COMMENT '四、利润总额（亏损总额以“-”号填列）',
  `income_tax_expense` varchar(64) DEFAULT NULL COMMENT '减：所得税费用',
  `net_profit` varchar(64) DEFAULT NULL COMMENT '五、净利润（净亏损以“-”号填列）',
  `continuing_operations_net` varchar(64) DEFAULT NULL COMMENT '（一）持续经营净利润（净亏损以“-”号填列）',
  `discontinued_operations_net` varchar(64) DEFAULT NULL COMMENT '（二）终止经营净利润（净亏损以“-”号填列）',
  `parent_company_net` varchar(64) DEFAULT NULL COMMENT '（一）归属于母公司股东的净利润（净亏损以“-”号填列）',
  `minority_interest_net` varchar(64) DEFAULT NULL COMMENT '（二）少数股东损益（净亏损以“-”号填列）',
  `oth_comprehensive_income` varchar(64) DEFAULT NULL COMMENT '六、其他综合收益的税后净额',
  `oci_not_reclassifiable` varchar(64) DEFAULT NULL COMMENT '（一）以后不能重分类进损益的其他综合收益',
  `pension_remeasurement` varchar(64) DEFAULT NULL COMMENT '1.重新计量设定受益计划变动额',
  `equity_method_oci_1` varchar(64) DEFAULT NULL COMMENT '2.权益法下不能转损益的其他综合收益',
  `equity_invest_fv_change` varchar(64) DEFAULT NULL COMMENT '3.其他权益工具投资公允价值变动',
  `credit_risk_fv_change` varchar(64) DEFAULT NULL COMMENT '4.企业自身信用风险公允价值变动',
  `oci_not_reclassifiable_other` varchar(64) DEFAULT NULL COMMENT '5.其他',
  `oci_reclassifiable` varchar(64) DEFAULT NULL COMMENT '（二）将重分类进损益的其他综合收益',
  `equity_method_oci_2` varchar(64) DEFAULT NULL COMMENT '1.权益法下可转损益的其他综合收益',
  `debt_invest_fv_change` varchar(64) DEFAULT NULL COMMENT '2.其他债权投资公允价值变动',
  `financial_asset_reclass` varchar(64) DEFAULT NULL COMMENT '3.金融资产重分类计入其他综合收益的金额',
  `debt_invest_impairment` varchar(64) DEFAULT NULL COMMENT '4.其他债权投资信用减值准备',
  `cash_flow_hedge` varchar(64) DEFAULT NULL COMMENT '5.现金流量套期储备',
  `foreign_currency_translation` varchar(64) DEFAULT NULL COMMENT '6.外币财务报表折算差额',
  `oci_reclassifiable_other` varchar(64) DEFAULT NULL COMMENT '7.其他',
  `total_comprehensive_income` varchar(64) DEFAULT NULL COMMENT '七、综合收益总额',
  `parent_company_oci` varchar(64) DEFAULT NULL COMMENT '（一）归属于母公司所有者的综合收益总额',
  `minority_interest_oci` varchar(64) DEFAULT NULL COMMENT '（二）归属于少数股东的综合收益总额',
  `earnings_per_share` varchar(64) DEFAULT NULL COMMENT '八、每股收益：',
  `eps_basic` varchar(64) DEFAULT NULL COMMENT '基本每股收益',
  `eps_diluted` varchar(64) DEFAULT NULL COMMENT '稀释每股收益',
  `update_flag` varchar(1) DEFAULT NULL COMMENT '更新标识',
  `created_at` datetime NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_ts_income_com_id` (`com_id`),
  KEY `ix_ts_income_user_id` (`user_id`),
  KEY `ix_ts_income_id` (`id`),
  KEY `ix_ts_income_end_date` (`end_date`),
  KEY `ix_ts_income_ts_code` (`ts_code`),
  KEY `ix_ts_income_year` (`year`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='利润表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user`
--

DROP TABLE IF EXISTS `user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user` (
  `id` varchar(32) NOT NULL,
  `create_time` bigint DEFAULT NULL COMMENT '创建时间',
  `create_date` datetime DEFAULT NULL COMMENT '创建日期',
  `update_time` bigint DEFAULT NULL COMMENT '更新时间',
  `update_date` datetime DEFAULT NULL COMMENT '更新日期',
  `access_token` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '令牌',
  `admin_access_token` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '管理员专属令牌',
  `nickname` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '名称',
  `password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '密码',
  `email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '邮箱',
  `avatar` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '用户头像URL/Base64字符串',
  `language` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '语言',
  `color_schema` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '界面主题配色（light/dark等）',
  `timezone` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '用户时区设置',
  `last_login_time` datetime DEFAULT NULL COMMENT '最后登录时间',
  `is_authenticated` varchar(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '是否已认证',
  `is_active` varchar(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '账户是否激活',
  `is_anonymous` varchar(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '是否匿名用户',
  `login_channel` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '登录渠道',
  `status` varchar(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '状态',
  `is_superuser` tinyint(1) DEFAULT NULL COMMENT '是否管理员',
  `created_by` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '创建人',
  `dept_id` bigint DEFAULT NULL COMMENT '部门ID',
  `user_name` varchar(100) DEFAULT NULL COMMENT '用户账号',
  `user_type` varchar(2) DEFAULT '00' COMMENT '用户类型（00系统用户）',
  `phonenumber` varchar(11) DEFAULT '' COMMENT '手机号码',
  `sex` char(1) DEFAULT '0' COMMENT '用户性别（0男 1女 2未知）',
  `user_status` char(1) DEFAULT '0' COMMENT '账号状态（0正常 1停用）',
  `del_flag` char(1) DEFAULT '0' COMMENT '删除标志（0代表存在 2代表删除）',
  `login_ip` varchar(128) DEFAULT '' COMMENT '最后登录IP',
  `login_date` datetime DEFAULT NULL COMMENT '最后登录时间',
  `pwd_update_date` datetime DEFAULT NULL COMMENT '密码最后更新时间',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '创建者',
  `update_by` varchar(64) DEFAULT '' COMMENT '更新者',
  `remark` varchar(500) DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`id`),
  KEY `user_create_time` (`create_time`),
  KEY `user_create_date` (`create_date`),
  KEY `user_update_time` (`update_time`),
  KEY `user_update_date` (`update_date`),
  KEY `user_access_token` (`access_token`),
  KEY `user_admin_access_token` (`admin_access_token`),
  KEY `user_nickname` (`nickname`),
  KEY `user_password` (`password`),
  KEY `user_email` (`email`),
  KEY `user_language` (`language`),
  KEY `user_color_schema` (`color_schema`),
  KEY `user_timezone` (`timezone`),
  KEY `user_last_login_time` (`last_login_time`),
  KEY `user_is_authenticated` (`is_authenticated`),
  KEY `user_is_active` (`is_active`),
  KEY `user_is_anonymous` (`is_anonymous`),
  KEY `user_login_channel` (`login_channel`),
  KEY `user_status` (`status`),
  KEY `user_is_superuser` (`is_superuser`),
  KEY `user_created_by` (`created_by`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='ragflow用户表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_canvas`
--

DROP TABLE IF EXISTS `user_canvas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user_canvas` (
  `id` varchar(32) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `avatar` text,
  `user_id` varchar(255) NOT NULL,
  `title` varchar(255) DEFAULT NULL,
  `permission` varchar(16) NOT NULL,
  `description` text,
  `canvas_type` varchar(32) DEFAULT NULL,
  `canvas_category` varchar(32) NOT NULL,
  `dsl` longtext,
  `agent_type` varchar(32) DEFAULT NULL,
  `agent_type_cn` varchar(255) DEFAULT NULL,
  `agent_type_en` varchar(255) DEFAULT NULL,
  `params` longtext,
  PRIMARY KEY (`id`),
  KEY `usercanvas_create_time` (`create_time`),
  KEY `usercanvas_create_date` (`create_date`),
  KEY `usercanvas_update_time` (`update_time`),
  KEY `usercanvas_update_date` (`update_date`),
  KEY `usercanvas_user_id` (`user_id`),
  KEY `usercanvas_permission` (`permission`),
  KEY `usercanvas_canvas_type` (`canvas_type`),
  KEY `usercanvas_canvas_category` (`canvas_category`),
  KEY `user_canvas_agent_type` (`agent_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_canvas_params`
--

DROP TABLE IF EXISTS `user_canvas_params`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user_canvas_params` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `canvas_id` varchar(32) NOT NULL,
  `name_cn` varchar(100) DEFAULT NULL,
  `name_en` varchar(100) DEFAULT NULL,
  `default_value` varchar(500) DEFAULT NULL,
  `param_type` varchar(32) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `usercanvasparams_create_time` (`create_time`),
  KEY `usercanvasparams_create_date` (`create_date`),
  KEY `usercanvasparams_update_time` (`update_time`),
  KEY `usercanvasparams_update_date` (`update_date`),
  KEY `usercanvasparams_canvas_id` (`canvas_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_canvas_version`
--

DROP TABLE IF EXISTS `user_canvas_version`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user_canvas_version` (
  `id` varchar(32) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `user_canvas_id` varchar(255) NOT NULL,
  `title` varchar(255) DEFAULT NULL,
  `description` text,
  `dsl` longtext,
  PRIMARY KEY (`id`),
  KEY `usercanvasversion_create_time` (`create_time`),
  KEY `usercanvasversion_create_date` (`create_date`),
  KEY `usercanvasversion_update_time` (`update_time`),
  KEY `usercanvasversion_update_date` (`update_date`),
  KEY `usercanvasversion_user_canvas_id` (`user_canvas_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_tenant`
--

DROP TABLE IF EXISTS `user_tenant`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user_tenant` (
  `id` varchar(32) NOT NULL,
  `create_time` bigint DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_time` bigint DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `user_id` varchar(32) NOT NULL,
  `tenant_id` varchar(32) NOT NULL,
  `role` varchar(32) NOT NULL,
  `invited_by` varchar(32) NOT NULL,
  `status` varchar(1) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `usertenant_create_time` (`create_time`),
  KEY `usertenant_create_date` (`create_date`),
  KEY `usertenant_update_time` (`update_time`),
  KEY `usertenant_update_date` (`update_date`),
  KEY `usertenant_user_id` (`user_id`),
  KEY `usertenant_tenant_id` (`tenant_id`),
  KEY `usertenant_role` (`role`),
  KEY `usertenant_invited_by` (`invited_by`),
  KEY `usertenant_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-07-23 16:32:19
