import asyncio
import logging
import copy
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from bson import ObjectId
import motor.motor_asyncio
from app.config import settings

logger = logging.getLogger("student_management.database")

# Collections list
COLLECTIONS = [
    "users",
    "students",
    "subjects",
    "classes",
    "attendance",
    "homework",
    "submissions",
    "exams",
    "fees",
    "payments",
    "settings",
    "class_feedback"
]

class MemoryCursor:
    """Async cursor compatible with Motor cursor for fallback/local test execution"""
    def __init__(self, docs: List[Dict[str, Any]]):
        self._docs = docs
        self._index = 0

    def sort(self, key_or_list, direction=1):
        if isinstance(key_or_list, list):
            for k, d in reversed(key_or_list):
                self._docs.sort(key=lambda x: (x.get(k) is None, x.get(k)), reverse=(d == -1))
        else:
            self._docs.sort(key=lambda x: (x.get(key_or_list) is None, x.get(key_or_list)), reverse=(direction == -1))
        return self

    def limit(self, n: int):
        self._docs = self._docs[:n]
        return self

    def skip(self, n: int):
        self._docs = self._docs[n:]
        return self

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index < len(self._docs):
            doc = self._docs[self._index]
            self._index += 1
            return copy.deepcopy(doc)
        raise StopAsyncIteration

    async def to_list(self, length: Optional[int] = None):
        if length is not None:
            return copy.deepcopy(self._docs[:length])
        return copy.deepcopy(self._docs)


class MemoryCollection:
    """Async MongoDB-compatible in-memory collection with ObjectId & date handling"""
    def __init__(self, name: str):
        self.name = name
        self.docs: Dict[str, Dict[str, Any]] = {}

    def _matches(self, doc: Dict[str, Any], query: Dict[str, Any]) -> bool:
        if not query:
            return True
        for k, v in query.items():
            if k == "$or" and isinstance(v, list):
                if not any(self._matches(doc, cond) for cond in v):
                    return False
                continue
            if k == "$and" and isinstance(v, list):
                if not all(self._matches(doc, cond) for cond in v):
                    return False
                continue

            doc_val = doc.get(k)
            if isinstance(v, dict):
                # Operator matching
                for op, op_val in v.items():
                    if op == "$eq" and doc_val != op_val:
                        return False
                    elif op == "$ne" and doc_val == op_val:
                        return False
                    elif op == "$in":
                        if isinstance(doc_val, list):
                            if not any(item in op_val for item in doc_val):
                                return False
                        elif doc_val not in op_val:
                            return False
                    elif op == "$nin":
                        if isinstance(doc_val, list):
                            if any(item in op_val for item in doc_val):
                                return False
                        elif doc_val in op_val:
                            return False
                    elif op == "$gt" and not (doc_val is not None and doc_val > op_val):
                        return False
                    elif op == "$gte" and not (doc_val is not None and doc_val >= op_val):
                        return False
                    elif op == "$lt" and not (doc_val is not None and doc_val < op_val):
                        return False
                    elif op == "$lte" and not (doc_val is not None and doc_val <= op_val):
                        return False
                    elif op == "$size":
                        if not isinstance(doc_val, list) or len(doc_val) != op_val:
                            return False
                    elif op == "$exists":
                        exists = k in doc
                        if exists != bool(op_val):
                            return False
                    elif op == "$regex":
                        import re
                        pattern = re.compile(op_val, re.IGNORECASE)
                        if not doc_val or not pattern.search(str(doc_val)):
                            return False
            elif isinstance(doc_val, list) and not isinstance(v, list):
                if v not in doc_val:
                    return False
            else:
                if doc_val != v:
                    return False
        return True

    def find(self, query: Optional[Dict[str, Any]] = None, projection: Optional[Dict[str, Any]] = None):
        query = query or {}
        matches = [d for d in self.docs.values() if self._matches(d, query)]
        return MemoryCursor(matches)

    async def find_one(self, query: Optional[Dict[str, Any]] = None, projection: Optional[Dict[str, Any]] = None):
        query = query or {}
        for d in self.docs.values():
            if self._matches(d, query):
                return copy.deepcopy(d)
        return None

    async def insert_one(self, doc: Dict[str, Any]):
        to_insert = copy.deepcopy(doc)
        if "_id" not in to_insert:
            to_insert["_id"] = ObjectId()
        _id_str = str(to_insert["_id"])
        self.docs[_id_str] = to_insert
        class Result:
            inserted_id = to_insert["_id"]
        return Result()

    async def insert_many(self, docs: List[Dict[str, Any]]):
        ids = []
        for d in docs:
            res = await self.insert_one(d)
            ids.append(res.inserted_id)
        class Result:
            inserted_ids = ids
        return Result()

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False):
        target_id = None
        for _id, d in self.docs.items():
            if self._matches(d, query):
                target_id = _id
                break

        matched_count = 1 if target_id else 0
        modified_count = 0

        if target_id:
            doc = self.docs[target_id]
            if "$set" in update:
                doc.update(copy.deepcopy(update["$set"]))
                modified_count = 1
            if "$addToSet" in update:
                for k, v in update["$addToSet"].items():
                    if k not in doc or not isinstance(doc[k], list):
                        doc[k] = []
                    if v not in doc[k]:
                        doc[k].append(v)
                modified_count = 1
            if "$inc" in update:
                for k, v in update["$inc"].items():
                    doc[k] = doc.get(k, 0) + v
                modified_count = 1
            if "$unset" in update:
                for k in update["$unset"]:
                    doc.pop(k, None)
                modified_count = 1
        elif upsert:
            new_doc = copy.deepcopy(query)
            if "$set" in update:
                new_doc.update(copy.deepcopy(update["$set"]))
            await self.insert_one(new_doc)
            matched_count = 0
            modified_count = 1

        class Result:
            pass
        res = Result()
        res.matched_count = matched_count
        res.modified_count = modified_count
        return res

    async def delete_one(self, query: Dict[str, Any]):
        target_id = None
        for _id, d in self.docs.items():
            if self._matches(d, query):
                target_id = _id
                break
        deleted_count = 0
        if target_id and target_id in self.docs:
            del self.docs[target_id]
            deleted_count = 1
        class Result:
            pass
        res = Result()
        res.deleted_count = deleted_count
        return res

    async def delete_many(self, query: Dict[str, Any]):
        to_delete = [k for k, d in self.docs.items() if self._matches(d, query)]
        for k in to_delete:
            del self.docs[k]
        class Result:
            pass
        res = Result()
        res.deleted_count = len(to_delete)
        return res

    async def count_documents(self, query: Optional[Dict[str, Any]] = None):
        query = query or {}
        return sum(1 for d in self.docs.values() if self._matches(d, query))

    async def create_index(self, keys, **kwargs):
        return "index_created"


class MemoryDatabase:
    """Mock database container"""
    def __init__(self, name: str):
        self.name = name
        self.collections: Dict[str, MemoryCollection] = {
            col: MemoryCollection(col) for col in COLLECTIONS
        }

    def __getitem__(self, item: str):
        if item not in self.collections:
            self.collections[item] = MemoryCollection(item)
        return self.collections[item]

    def __getattr__(self, item: str):
        if item.startswith("_"):
            raise AttributeError(item)
        return self[item]

    def get_collection(self, item: str):
        return self[item]


class DatabaseManager:
    """MongoDB Atlas Database Connection Manager with seamless fallback"""
    def __init__(self):
        self.client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
        self.db = None
        self.is_atlas: bool = False
        self.connection_status: str = "disconnected"

    async def connect(self):
        uri = settings.MONGODB_URI
        # If user has configured a mongodb or mongodb+srv URI
        if uri and ("mongodb://" in uri or "mongodb+srv://" in uri):
            try:
                logger.info(f"Connecting to MongoDB at: {uri.split('@')[-1] if '@' in uri else uri}")
                # Motor client with 3-second timeout for quick fallback if offline
                motor_client = motor.motor_asyncio.AsyncIOMotorClient(
                    uri,
                    serverSelectionTimeoutMS=3000,
                    connectTimeoutMS=3000
                )
                # Test connection with ping command
                await motor_client.admin.command('ping')
                self.client = motor_client
                self.db = self.client[settings.DATABASE_NAME]
                self.is_atlas = True
                self.connection_status = "connected_atlas"
                logger.info(f"Successfully connected to MongoDB Atlas database '{settings.DATABASE_NAME}'!")
                await self.create_indexes()
                return
            except Exception as e:
                logger.warning(f"Could not connect to live MongoDB Atlas: {e}. Activating robust local in-memory fallback engine.")
                self.connection_status = f"offline_fallback: {e}"
        else:
            logger.info("No MongoDB Atlas URI provided. Using robust local storage engine.")

        # Fallback to high-performance local memory database
        self.db = MemoryDatabase(settings.DATABASE_NAME)
        self.is_atlas = False
        if not self.connection_status.startswith("offline_fallback"):
            self.connection_status = "local_memory"

    async def disconnect(self):
        if self.client:
            self.client.close()
            self.client = None
            logger.info("MongoDB client disconnected.")

    async def create_indexes(self):
        """Setup MongoDB indexes for commonly queried fields as specified"""
        if not self.db:
            return
        try:
            # Users indexes
            await self.db.users.create_index("email", unique=True)
            await self.db.users.create_index("studentId")

            # Students indexes
            await self.db.students.create_index("userId")
            await self.db.students.create_index("email")
            await self.db.students.create_index("enrollmentStatus")
            await self.db.students.create_index("name")

            # Classes indexes (date index for calendar and upcoming query)
            await self.db.classes.create_index("date")
            await self.db.classes.create_index("subject")
            await self.db.classes.create_index("assignedStudentIds")

            # Attendance indexes (compound unique index for classId + studentId)
            await self.db.attendance.create_index([("classId", 1), ("studentId", 1)], unique=True)
            await self.db.attendance.create_index("studentId")

            # Homework indexes (due date index for homework due soon / overdue)
            await self.db.homework.create_index("dueDate")
            await self.db.homework.create_index("assignedDate")
            await self.db.homework.create_index("assignedStudentIds")

            # Submissions indexes (compound unique index for homeworkId + studentId)
            await self.db.submissions.create_index([("homeworkId", 1), ("studentId", 1)], unique=True)
            await self.db.submissions.create_index("studentId")
            await self.db.submissions.create_index("status")

            # Fees indexes (studentId and dueDate for balance & overdue calculations)
            await self.db.fees.create_index("studentId")
            await self.db.fees.create_index("dueDate")

            # Payments indexes (studentId, feeId, paidAt)
            await self.db.payments.create_index("studentId")
            await self.db.payments.create_index("feeId")
            await self.db.payments.create_index("paidAt")
            await self.db.payments.create_index("createdAt")

            # Exams indexes
            await self.db.exams.create_index("date")
            await self.db.exams.create_index("subject")

            logger.info("MongoDB Atlas indexes verified/created successfully.")
        except Exception as e:
            logger.warning(f"Index creation note: {e}")

def serialize_mongo(obj: Any) -> Any:
    """Recursively converts BSON ObjectId, datetime, etc. into JSON serializable structures"""
    if isinstance(obj, list):
        return [serialize_mongo(item) for item in obj]
    elif isinstance(obj, dict):
        res = {}
        for k, v in obj.items():
            if k == "_id":
                res["id"] = str(v)
            elif isinstance(v, ObjectId):
                res[k] = str(v)
            elif isinstance(v, (dict, list)):
                res[k] = serialize_mongo(v)
            else:
                res[k] = v
        if "_id" in obj and "id" not in res:
            res["id"] = str(obj["_id"])
        return res
    elif isinstance(obj, ObjectId):
        return str(obj)
    return obj

db_manager = DatabaseManager()

def get_database():
    return db_manager.db
