-- MySQL dump 10.13  Distrib 8.4.11, for Linux (x86_64)
--
-- Host: localhost    Database: HMS_aiml_22
-- ------------------------------------------------------
-- Server version	8.4.11-0ubuntu0.26.04.1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `APPOINTMENT`
--

DROP TABLE IF EXISTS `APPOINTMENT`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `APPOINTMENT` (
  `AppointmentID` int NOT NULL,
  `PatientID` int DEFAULT NULL,
  `DoctorID` int DEFAULT NULL,
  `AppointmentDate` date DEFAULT NULL,
  `AppointmentTime` time DEFAULT NULL,
  `Status` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`AppointmentID`),
  KEY `PatientID` (`PatientID`),
  KEY `DoctorID` (`DoctorID`),
  CONSTRAINT `APPOINTMENT_ibfk_1` FOREIGN KEY (`PatientID`) REFERENCES `PATIENT` (`PatientID`),
  CONSTRAINT `APPOINTMENT_ibfk_2` FOREIGN KEY (`DoctorID`) REFERENCES `DOCTOR` (`DoctorID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `APPOINTMENT`
--

LOCK TABLES `APPOINTMENT` WRITE;
/*!40000 ALTER TABLE `APPOINTMENT` DISABLE KEYS */;
INSERT INTO `APPOINTMENT` VALUES (301,101,201,'2026-08-20','09:00:00','Scheduled'),(302,102,202,'2026-08-20','09:30:00','Scheduled'),(303,103,203,'2026-08-20','10:00:00','Completed'),(304,104,204,'2026-08-21','10:30:00','Scheduled'),(305,105,205,'2026-08-21','11:00:00','Cancelled'),(306,106,206,'2026-08-21','11:30:00','Scheduled'),(307,107,207,'2026-08-22','09:00:00','Completed'),(308,108,208,'2026-08-22','09:30:00','Scheduled'),(309,109,209,'2026-08-22','10:00:00','Scheduled'),(310,110,210,'2026-08-23','10:30:00','Scheduled');
/*!40000 ALTER TABLE `APPOINTMENT` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `BILL`
--

DROP TABLE IF EXISTS `BILL`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `BILL` (
  `BillID` int NOT NULL,
  `PatientID` int NOT NULL,
  `BillDate` date DEFAULT NULL,
  `TotalAmount` decimal(10,2) DEFAULT NULL,
  `AmountPaid` decimal(10,2) DEFAULT NULL,
  `PaymentStatus` varchar(30) DEFAULT NULL,
  PRIMARY KEY (`BillID`),
  KEY `PatientID` (`PatientID`),
  CONSTRAINT `BILL_ibfk_1` FOREIGN KEY (`PatientID`) REFERENCES `PATIENT` (`PatientID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `BILL`
--

LOCK TABLES `BILL` WRITE;
/*!40000 ALTER TABLE `BILL` DISABLE KEYS */;
INSERT INTO `BILL` VALUES (1,101,'2026-08-01',1500.00,1500.00,'Paid'),(2,102,'2026-08-02',2000.00,2000.00,'Paid'),(3,103,'2026-08-03',5000.00,3000.00,'Partial'),(4,104,'2026-08-04',1800.00,1800.00,'Paid'),(5,105,'2026-08-05',2500.00,1000.00,'Partial'),(6,106,'2026-08-06',1200.00,1200.00,'Paid'),(7,107,'2026-08-07',2200.00,2200.00,'Paid'),(8,108,'2026-08-08',3500.00,0.00,'Pending'),(9,109,'2026-08-09',1600.00,1600.00,'Paid'),(10,110,'2026-08-10',2800.00,1400.00,'Partial');
/*!40000 ALTER TABLE `BILL` ENABLE KEYS */;
UNLOCK TABLES;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8mb4 */ ;
/*!50003 SET character_set_results = utf8mb4 */ ;
/*!50003 SET collation_connection  = utf8mb4_0900_ai_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 DEFINER=`Alekhya_aiml_22`@`localhost`*/ /*!50003 TRIGGER `after_bill_update` AFTER UPDATE ON `BILL` FOR EACH ROW INSERT INTO Bill_Update_LOG (BillID, OldTotalAmount, NewTotalAmount, UpdatedAt) VALUES (OLD.BillID, OLD.TotalAmount, NEW.TotalAmount, NOW()) */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;

--
-- Table structure for table `Bill_Update_LOG`
--

DROP TABLE IF EXISTS `Bill_Update_LOG`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `Bill_Update_LOG` (
  `LogID` int NOT NULL AUTO_INCREMENT,
  `BillID` int DEFAULT NULL,
  `OldTotalAmount` decimal(10,2) DEFAULT NULL,
  `NewTotalAmount` decimal(10,2) DEFAULT NULL,
  `UpdatedAt` datetime DEFAULT NULL,
  PRIMARY KEY (`LogID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Bill_Update_LOG`
--

LOCK TABLES `Bill_Update_LOG` WRITE;
/*!40000 ALTER TABLE `Bill_Update_LOG` DISABLE KEYS */;
/*!40000 ALTER TABLE `Bill_Update_LOG` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `DEPARTMENT`
--

DROP TABLE IF EXISTS `DEPARTMENT`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `DEPARTMENT` (
  `DepartmentID` int NOT NULL,
  `DepartmentName` varchar(100) NOT NULL,
  `Location` varchar(100) DEFAULT NULL,
  `Phone` varchar(15) DEFAULT NULL,
  PRIMARY KEY (`DepartmentID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `DEPARTMENT`
--

LOCK TABLES `DEPARTMENT` WRITE;
/*!40000 ALTER TABLE `DEPARTMENT` DISABLE KEYS */;
INSERT INTO `DEPARTMENT` VALUES (1,'Cardiology','1st Floor','03340000001'),(2,'Neurology','2nd Floor','03340000002'),(3,'Orthopedics','3rd Floor','03340000003'),(4,'Dermatology','4th Floor','03340000004'),(5,'Pediatrics','5th Floor','03340000005'),(6,'Gynecology','6th Floor','03340000006'),(7,'General Medicine','1st Floor','03340000007'),(8,'ENT','2nd Floor','03340000008'),(9,'Ophthalmology','3rd Floor','03340000009'),(10,'Radiology','4th Floor','03340000010');
/*!40000 ALTER TABLE `DEPARTMENT` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `DOCTOR`
--

DROP TABLE IF EXISTS `DOCTOR`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `DOCTOR` (
  `DoctorID` int NOT NULL,
  `FirstName` varchar(50) NOT NULL,
  `LastName` varchar(50) NOT NULL,
  `Specialization` varchar(100) NOT NULL,
  `Phone` varchar(15) DEFAULT NULL,
  `Email` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`DoctorID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `DOCTOR`
--

LOCK TABLES `DOCTOR` WRITE;
/*!40000 ALTER TABLE `DOCTOR` DISABLE KEYS */;
INSERT INTO `DOCTOR` VALUES (201,'Rajesh','Kumar','Cardiologist','9000000001','rajesh@hospital.com'),(202,'Anita','Sharma','Dermatologist','9000000002','anita@hospital.com'),(203,'Amit','Roy','Neurologist','9000000003','amit@hospital.com'),(204,'Priya','Das','Pediatrician','9000000004','priya@hospital.com'),(205,'Sourav','Sen','Orthopedic','9000000005','sourav@hospital.com'),(206,'Neha','Ghosh','Gynecologist','9000000006','neha@hospital.com'),(207,'Arjun','Dutta','General Physician','9000000007','arjun@hospital.com'),(208,'Sneha','Roy','ENT Specialist','9000000008','sneha@hospital.com'),(209,'Vikash','Das','Surgeon','9000000009','vikash@hospital.com'),(210,'Riya','Sen','Psychiatrist','9000000010','riya@hospital.com');
/*!40000 ALTER TABLE `DOCTOR` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `MEDICAL_RECORD`
--

DROP TABLE IF EXISTS `MEDICAL_RECORD`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `MEDICAL_RECORD` (
  `RecordID` int NOT NULL,
  `PatientID` int NOT NULL,
  `DoctorID` int NOT NULL,
  `Diagnosis` varchar(200) DEFAULT NULL,
  `Prescription` varchar(500) DEFAULT NULL,
  `Treatment` varchar(300) DEFAULT NULL,
  `Notes` varchar(500) DEFAULT NULL,
  PRIMARY KEY (`RecordID`),
  KEY `PatientID` (`PatientID`),
  KEY `DoctorID` (`DoctorID`),
  CONSTRAINT `MEDICAL_RECORD_ibfk_1` FOREIGN KEY (`PatientID`) REFERENCES `PATIENT` (`PatientID`),
  CONSTRAINT `MEDICAL_RECORD_ibfk_2` FOREIGN KEY (`DoctorID`) REFERENCES `DOCTOR` (`DoctorID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `MEDICAL_RECORD`
--

LOCK TABLES `MEDICAL_RECORD` WRITE;
/*!40000 ALTER TABLE `MEDICAL_RECORD` DISABLE KEYS */;
INSERT INTO `MEDICAL_RECORD` VALUES (1,101,201,'Viral Fever','Paracetamol','Medication','Rest required'),(2,102,202,'Migraine','Painkiller','Medication','Avoid stress'),(3,103,203,'Chest Pain','Aspirin','Observation','Regular checkup'),(4,104,204,'Skin Allergy','Antihistamine','Medication','Avoid allergens'),(5,105,205,'Back Pain','Pain Reliever','Physiotherapy','Exercise recommended'),(6,106,201,'Common Cold','Cough Syrup','Medication','Drink warm water'),(7,107,202,'Migraine','Sumatriptan','Medication','Adequate sleep'),(8,108,203,'Diabetes','Metformin','Medication','Control sugar intake'),(9,109,204,'Allergy','Cetirizine','Medication','Follow-up required'),(10,110,205,'Joint Pain','Painkiller','Physiotherapy','Regular exercise');
/*!40000 ALTER TABLE `MEDICAL_RECORD` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `PATIENT`
--

DROP TABLE IF EXISTS `PATIENT`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `PATIENT` (
  `PatientID` int NOT NULL,
  `FirstName` varchar(50) NOT NULL,
  `LastName` varchar(50) NOT NULL,
  `DOB` date DEFAULT NULL,
  `Gender` varchar(10) DEFAULT NULL,
  `Phone` varchar(15) DEFAULT NULL,
  `Email` varchar(100) DEFAULT NULL,
  `Address` varchar(255) DEFAULT NULL,
  `BloodGroup` varchar(5) DEFAULT NULL,
  PRIMARY KEY (`PatientID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `PATIENT`
--

LOCK TABLES `PATIENT` WRITE;
/*!40000 ALTER TABLE `PATIENT` DISABLE KEYS */;
INSERT INTO `PATIENT` VALUES (101,'Rahul','Sharma','1995-05-12','Male','9876543210','rahul@gmail.com','Kolkata','B+'),(102,'Priya','Das','1998-08-20','Female','9876543211','priya@gmail.com','Howrah','A+'),(103,'Amit','Roy','1990-03-15','Male','9876543212','amit@gmail.com','Durgapur','O+'),(104,'Sneha','Ghosh','2000-11-10','Female','9876543213','sneha@gmail.com','Siliguri','AB+'),(105,'Arjun','Sen','1988-07-25','Male','9876543214','arjun@gmail.com','Kolkata','A-'),(106,'Riya','Banerjee','1997-01-18','Female','9876543215','riya@gmail.com','Bardhaman','O+'),(107,'Sourav','Dutta','1993-09-05','Male','9876543216','sourav@gmail.com','Kolkata','B+'),(108,'Ananya','Mukherjee','2001-04-22','Female','9876543217','ananya@gmail.com','Howrah','AB-'),(109,'Vikash','Chatterjee','1985-12-30','Male','9876543218','vikash@gmail.com','Durgapur','O+'),(110,'Moumita','Das','1999-06-14','Female','9876543219','moumita@gmail.com','Kolkata','A+');
/*!40000 ALTER TABLE `PATIENT` ENABLE KEYS */;
UNLOCK TABLES;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8mb4 */ ;
/*!50003 SET character_set_results = utf8mb4 */ ;
/*!50003 SET collation_connection  = utf8mb4_0900_ai_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 DEFINER=`Alekhya_aiml_22`@`localhost`*/ /*!50003 TRIGGER `after_patient_insert` AFTER INSERT ON `PATIENT` FOR EACH ROW INSERT INTO patient_LOG (PatientID, PatientName, Action, LogTimestamp) VALUES (NEW.PatientID, CONCAT(NEW.FirstName, ' ', NEW.LastName), 'INSERT', NOW()) */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8mb4 */ ;
/*!50003 SET character_set_results = utf8mb4 */ ;
/*!50003 SET collation_connection  = utf8mb4_0900_ai_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 DEFINER=`Alekhya_aiml_22`@`localhost`*/ /*!50003 TRIGGER `after_patient_delete` AFTER DELETE ON `PATIENT` FOR EACH ROW INSERT INTO deleted_Patient_log (PatientID, PatientName, DeletedAt) VALUES (OLD.PatientID, CONCAT(OLD.FirstName, ' ', OLD.LastName), NOW()) */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;

--
-- Table structure for table `PAYMENT`
--

DROP TABLE IF EXISTS `PAYMENT`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `PAYMENT` (
  `PaymentID` int NOT NULL,
  `BillID` int NOT NULL,
  `PaymentDate` date DEFAULT NULL,
  `Amount` decimal(10,2) DEFAULT NULL,
  `PaymentMode` varchar(30) DEFAULT NULL,
  `TransactionNo` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`PaymentID`),
  KEY `BillID` (`BillID`),
  CONSTRAINT `PAYMENT_ibfk_1` FOREIGN KEY (`BillID`) REFERENCES `BILL` (`BillID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `PAYMENT`
--

LOCK TABLES `PAYMENT` WRITE;
/*!40000 ALTER TABLE `PAYMENT` DISABLE KEYS */;
INSERT INTO `PAYMENT` VALUES (1,1,'2026-08-01',1500.00,'Cash','TXN001'),(2,2,'2026-08-02',2000.00,'UPI','TXN002'),(3,3,'2026-08-03',3000.00,'Card','TXN003'),(4,4,'2026-08-04',1800.00,'UPI','TXN004'),(5,5,'2026-08-05',1000.00,'Cash','TXN005'),(6,6,'2026-08-06',1200.00,'Card','TXN006'),(7,7,'2026-08-07',2200.00,'UPI','TXN007'),(8,8,'2026-08-08',0.00,'Cash','TXN008'),(9,9,'2026-08-09',1600.00,'UPI','TXN009'),(10,10,'2026-08-10',1400.00,'Card','TXN010');
/*!40000 ALTER TABLE `PAYMENT` ENABLE KEYS */;
UNLOCK TABLES;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8mb4 */ ;
/*!50003 SET character_set_results = utf8mb4 */ ;
/*!50003 SET collation_connection  = utf8mb4_0900_ai_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 DEFINER=`Alekhya_aiml_22`@`localhost`*/ /*!50003 TRIGGER `after_payment_insert` AFTER INSERT ON `PAYMENT` FOR EACH ROW INSERT INTO Payment_LOG (PaymentID, Amount, PaymentDate, LogTimestamp) VALUES (NEW.PaymentID, NEW.Amount, NEW.PaymentDate, NOW()) */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;

--
-- Table structure for table `Payment_LOG`
--

DROP TABLE IF EXISTS `Payment_LOG`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `Payment_LOG` (
  `LogID` int NOT NULL AUTO_INCREMENT,
  `PaymentID` int DEFAULT NULL,
  `Amount` decimal(10,2) DEFAULT NULL,
  `PaymentDate` date DEFAULT NULL,
  `LogTimestamp` datetime DEFAULT NULL,
  PRIMARY KEY (`LogID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Payment_LOG`
--

LOCK TABLES `Payment_LOG` WRITE;
/*!40000 ALTER TABLE `Payment_LOG` DISABLE KEYS */;
/*!40000 ALTER TABLE `Payment_LOG` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `ROOM`
--

DROP TABLE IF EXISTS `ROOM`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ROOM` (
  `RoomID` int NOT NULL,
  `RoomNo` varchar(20) DEFAULT NULL,
  `RoomType` varchar(50) DEFAULT NULL,
  `Floor` int DEFAULT NULL,
  `Status` varchar(30) DEFAULT NULL,
  `DailyCharge` decimal(10,2) DEFAULT NULL,
  `DepartmentID` int DEFAULT NULL,
  PRIMARY KEY (`RoomID`),
  UNIQUE KEY `RoomNo` (`RoomNo`),
  KEY `DepartmentID` (`DepartmentID`),
  CONSTRAINT `ROOM_ibfk_1` FOREIGN KEY (`DepartmentID`) REFERENCES `DEPARTMENT` (`DepartmentID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ROOM`
--

LOCK TABLES `ROOM` WRITE;
/*!40000 ALTER TABLE `ROOM` DISABLE KEYS */;
INSERT INTO `ROOM` VALUES (1,'101','General',1,'Available',1000.00,1),(2,'102','General',1,'Occupied',1000.00,1),(3,'201','Private',2,'Available',2500.00,2),(4,'202','Private',2,'Occupied',2500.00,2),(5,'301','ICU',3,'Occupied',5000.00,3),(6,'302','ICU',3,'Available',5000.00,3),(7,'401','General',4,'Available',1000.00,4),(8,'402','Private',4,'Occupied',2500.00,4),(9,'501','General',5,'Available',1000.00,5),(10,'502','Private',5,'Available',2500.00,5);
/*!40000 ALTER TABLE `ROOM` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `STAFF`
--

DROP TABLE IF EXISTS `STAFF`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `STAFF` (
  `StaffID` int NOT NULL,
  `FirstName` varchar(50) NOT NULL,
  `LastName` varchar(50) DEFAULT NULL,
  `Role` varchar(50) DEFAULT NULL,
  `Phone` varchar(15) DEFAULT NULL,
  `Email` varchar(100) DEFAULT NULL,
  `RoomID` int DEFAULT NULL,
  PRIMARY KEY (`StaffID`),
  KEY `RoomID` (`RoomID`),
  CONSTRAINT `STAFF_ibfk_1` FOREIGN KEY (`RoomID`) REFERENCES `ROOM` (`RoomID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `STAFF`
--

LOCK TABLES `STAFF` WRITE;
/*!40000 ALTER TABLE `STAFF` DISABLE KEYS */;
INSERT INTO `STAFF` VALUES (1,'Ramesh','Kumar','Nurse','9000000001','ramesh@gmail.com',1),(2,'Sita','Das','Nurse','9000000002','sita@gmail.com',2),(3,'Anil','Roy','Ward Boy','9000000003','anil@gmail.com',3),(4,'Mina','Ghosh','Nurse','9000000004','mina@gmail.com',4),(5,'Raj','Sen','Receptionist','9000000005','raj@gmail.com',5),(6,'Puja','Das','Nurse','9000000006','puja@gmail.com',6),(7,'Karan','Dutta','Ward Boy','9000000007','karan@gmail.com',7),(8,'Tina','Roy','Nurse','9000000008','tina@gmail.com',8),(9,'Suman','Pal','Receptionist','9000000009','suman@gmail.com',9),(10,'Neha','Sen','Nurse','9000000010','neha@gmail.com',10);
/*!40000 ALTER TABLE `STAFF` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `TEST`
--

DROP TABLE IF EXISTS `TEST`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `TEST` (
  `TestID` int NOT NULL,
  `TestName` varchar(100) NOT NULL,
  `TestType` varchar(100) DEFAULT NULL,
  `Cost` decimal(10,2) DEFAULT NULL,
  PRIMARY KEY (`TestID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `TEST`
--

LOCK TABLES `TEST` WRITE;
/*!40000 ALTER TABLE `TEST` DISABLE KEYS */;
INSERT INTO `TEST` VALUES (1,'Complete Blood Count','Blood Test',500.00),(2,'Blood Sugar','Blood Test',300.00),(3,'Lipid Profile','Blood Test',800.00),(4,'Urine Test','Urine Test',250.00),(5,'X-Ray Chest','Imaging',1000.00),(6,'ECG','Cardiac Test',700.00),(7,'MRI Brain','Imaging',5000.00),(8,'CT Scan','Imaging',4000.00),(9,'Thyroid Test','Blood Test',600.00),(10,'Liver Function Test','Blood Test',900.00);
/*!40000 ALTER TABLE `TEST` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `TEST_RESULT`
--

DROP TABLE IF EXISTS `TEST_RESULT`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `TEST_RESULT` (
  `ResultID` int NOT NULL,
  `TestID` int NOT NULL,
  `PatientID` int NOT NULL,
  `ResultValue` varchar(200) DEFAULT NULL,
  `Unit` varchar(50) DEFAULT NULL,
  `NormalRange` varchar(100) DEFAULT NULL,
  `ResultDate` date DEFAULT NULL,
  PRIMARY KEY (`ResultID`),
  KEY `TestID` (`TestID`),
  KEY `PatientID` (`PatientID`),
  CONSTRAINT `TEST_RESULT_ibfk_1` FOREIGN KEY (`TestID`) REFERENCES `TEST` (`TestID`),
  CONSTRAINT `TEST_RESULT_ibfk_2` FOREIGN KEY (`PatientID`) REFERENCES `PATIENT` (`PatientID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `TEST_RESULT`
--

LOCK TABLES `TEST_RESULT` WRITE;
/*!40000 ALTER TABLE `TEST_RESULT` DISABLE KEYS */;
INSERT INTO `TEST_RESULT` VALUES (1,1,101,'Normal','-','Normal','2026-08-01'),(2,2,102,'95','mg/dL','70-100','2026-08-02'),(3,3,103,'210','mg/dL','Below 200','2026-08-03'),(4,4,104,'Normal','-','Normal','2026-08-04'),(5,5,105,'Normal','-','Normal','2026-08-05'),(6,6,106,'Normal','-','Normal','2026-08-06'),(7,7,107,'Normal','-','Normal','2026-08-07'),(8,8,108,'Mild Abnormality','-','Normal','2026-08-08'),(9,9,109,'4.2','mIU/L','0.4-4.0','2026-08-09'),(10,10,110,'Normal','-','Normal','2026-08-10');
/*!40000 ALTER TABLE `TEST_RESULT` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `deleted_Patient_log`
--

DROP TABLE IF EXISTS `deleted_Patient_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `deleted_Patient_log` (
  `LogID` int NOT NULL AUTO_INCREMENT,
  `PatientID` int DEFAULT NULL,
  `PatientName` varchar(100) DEFAULT NULL,
  `DeletedAt` datetime DEFAULT NULL,
  PRIMARY KEY (`LogID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `deleted_Patient_log`
--

LOCK TABLES `deleted_Patient_log` WRITE;
/*!40000 ALTER TABLE `deleted_Patient_log` DISABLE KEYS */;
/*!40000 ALTER TABLE `deleted_Patient_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Temporary view structure for view `doctor_medical_record_view`
--

DROP TABLE IF EXISTS `doctor_medical_record_view`;
/*!50001 DROP VIEW IF EXISTS `doctor_medical_record_view`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `doctor_medical_record_view` AS SELECT 
 1 AS `DoctorName`,
 1 AS `Specialization`,
 1 AS `PatientID`,
 1 AS `Diagnosis`,
 1 AS `Treatment`*/;
SET character_set_client = @saved_cs_client;

--
-- Table structure for table `patient_LOG`
--

DROP TABLE IF EXISTS `patient_LOG`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `patient_LOG` (
  `LogID` int NOT NULL AUTO_INCREMENT,
  `PatientID` int DEFAULT NULL,
  `PatientName` varchar(100) DEFAULT NULL,
  `Action` varchar(50) DEFAULT NULL,
  `LogTimestamp` datetime DEFAULT NULL,
  PRIMARY KEY (`LogID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `patient_LOG`
--

LOCK TABLES `patient_LOG` WRITE;
/*!40000 ALTER TABLE `patient_LOG` DISABLE KEYS */;
/*!40000 ALTER TABLE `patient_LOG` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Final view structure for view `doctor_medical_record_view`
--

/*!50001 DROP VIEW IF EXISTS `doctor_medical_record_view`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`Alekhya_aiml_22`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `doctor_medical_record_view` AS select concat(`d`.`FirstName`,' ',`d`.`LastName`) AS `DoctorName`,`d`.`Specialization` AS `Specialization`,`m`.`PatientID` AS `PatientID`,`m`.`Diagnosis` AS `Diagnosis`,`m`.`Treatment` AS `Treatment` from (`DOCTOR` `d` join `MEDICAL_RECORD` `m` on((`d`.`DoctorID` = `m`.`DoctorID`))) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-10-23  7:57:43
