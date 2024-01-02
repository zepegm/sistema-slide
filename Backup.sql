-- MySQL dump 10.13  Distrib 8.0.26, for Win64 (x86_64)
--
-- Host: localhost    Database: sistema-slide
-- ------------------------------------------------------
-- Server version	8.0.26

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `categoria_departamentos`
--

DROP TABLE IF EXISTS `categoria_departamentos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `categoria_departamentos` (
  `id` smallint NOT NULL AUTO_INCREMENT,
  `descricao` varchar(45) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `categoria_departamentos`
--

LOCK TABLES `categoria_departamentos` WRITE;
/*!40000 ALTER TABLE `categoria_departamentos` DISABLE KEYS */;
INSERT INTO `categoria_departamentos` VALUES (1,'Ministério de Louvor'),(2,'Jovens/Adolescentes'),(3,'Departamentos'),(4,'Avulsos');
/*!40000 ALTER TABLE `categoria_departamentos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `categoria_slide`
--

DROP TABLE IF EXISTS `categoria_slide`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `categoria_slide` (
  `id` int NOT NULL AUTO_INCREMENT,
  `descricao` varchar(45) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `categoria_slide`
--

LOCK TABLES `categoria_slide` WRITE;
/*!40000 ALTER TABLE `categoria_slide` DISABLE KEYS */;
INSERT INTO `categoria_slide` VALUES (1,'Letra'),(2,'Coro'),(3,'Pausa inst.');
/*!40000 ALTER TABLE `categoria_slide` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `musicas`
--

DROP TABLE IF EXISTS `musicas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `musicas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `titulo` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `musicas`
--

LOCK TABLES `musicas` WRITE;
/*!40000 ALTER TABLE `musicas` DISABLE KEYS */;
/*!40000 ALTER TABLE `musicas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `status_vinculo`
--

DROP TABLE IF EXISTS `status_vinculo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `status_vinculo` (
  `id` smallint NOT NULL AUTO_INCREMENT,
  `descricao` varchar(45) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `status_vinculo`
--

LOCK TABLES `status_vinculo` WRITE;
/*!40000 ALTER TABLE `status_vinculo` DISABLE KEYS */;
INSERT INTO `status_vinculo` VALUES (1,'Forte'),(2,'Médio'),(3,'Fraco');
/*!40000 ALTER TABLE `status_vinculo` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `subcategoria_departamentos`
--

DROP TABLE IF EXISTS `subcategoria_departamentos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `subcategoria_departamentos` (
  `id` smallint NOT NULL AUTO_INCREMENT,
  `descricao` varchar(45) NOT NULL,
  `supercategoria` smallint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `supercategoria_idx` (`supercategoria`),
  CONSTRAINT `supercategoria` FOREIGN KEY (`supercategoria`) REFERENCES `categoria_departamentos` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `subcategoria_departamentos`
--

LOCK TABLES `subcategoria_departamentos` WRITE;
/*!40000 ALTER TABLE `subcategoria_departamentos` DISABLE KEYS */;
INSERT INTO `subcategoria_departamentos` VALUES (1,'Corinhos Congregacionais',1),(2,'Formação Atual',1),(3,'Formações Anteriores',1),(4,'Retiros e Eventos da Juventude',1),(5,'Eventos de Páscoa',1),(6,'Eventos de Natal',1),(7,'Santa Ceia',1),(8,'Mocidade Local',2),(9,'UMADECAP',2),(10,'ADUNAD',2),(11,'Dep. Infantil',3),(12,'Dep. Feminino',3),(13,'Dep. Masculino',3),(14,'Orquestra',4),(15,'Geral',4);
/*!40000 ALTER TABLE `subcategoria_departamentos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `vinculos_x_musicas`
--

DROP TABLE IF EXISTS `vinculos_x_musicas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `vinculos_x_musicas` (
  `id_musica` int NOT NULL,
  `id_vinculo` smallint NOT NULL,
  `id_status` smallint NOT NULL,
  `descricao` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`id_musica`,`id_vinculo`),
  KEY `id_vinculo_idx` (`id_vinculo`),
  KEY `id_status_idx` (`id_status`),
  CONSTRAINT `id_status` FOREIGN KEY (`id_status`) REFERENCES `status_vinculo` (`id`),
  CONSTRAINT `id_vinculo` FOREIGN KEY (`id_vinculo`) REFERENCES `subcategoria_departamentos` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `vinculos_x_musicas`
--

LOCK TABLES `vinculos_x_musicas` WRITE;
/*!40000 ALTER TABLE `vinculos_x_musicas` DISABLE KEYS */;
/*!40000 ALTER TABLE `vinculos_x_musicas` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-01-02 16:59:25
