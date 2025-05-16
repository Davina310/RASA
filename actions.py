import json
from pathlib import Path
from typing import Dict, Text, Any, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
class ActionSuggestMajor(Action):
    def name(self) -> Text:
        return "action_suggest_major"
        

    def load_majors(self) -> List[Dict]:
        """تحميل قائمة التخصصات من ملف JSON"""
        try:
            current_dir = Path(__file__).parent
            file_path = current_dir.parent / "data" / "majors.json"
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, list):
                    raise ValueError("ملف JSON يجب أن يحتوي على مصفوفة في المستوى العلوي")
                return data
        except Exception as e:
            print(f"⚠️ خطأ في تحميل ملف التخصصات: {str(e)}")
            return []

    def get_slot_as_list(self, tracker: Tracker, slot_name: Text) -> List:
        """تحويل قيمة السلوة إلى قائمة"""
        value = tracker.get_slot(slot_name)
        if value is None:
            return []
        return [value] if isinstance(value, str) else value

    def calculate_match_score(self, major: Dict, tracker: Tracker) -> float:
        """حساب درجة التوافق بين المستخدم والتخصص"""
        try:
            score = 0.0
            weights = {
                "subjects": 4.0,
                "skills": 3.5,
                "thinking_style": 3.0,
                "learning_style": 2.5,
                "work_nature": 2.0
            }
            
            user_data = {
                "subjects": self.get_slot_as_list(tracker, "subject"),
                "skills": self.get_slot_as_list(tracker, "skill"),
                "thinking_style": self.get_slot_as_list(tracker, "thinking_style"),
                "learning_style": self.get_slot_as_list(tracker, "learning_style"),
                "work_nature": self.get_slot_as_list(tracker, "work_nature")
            }
            
            for key in user_data:
                if key in major:
                    user_values = set(user_data[key])
                    major_values = set(major[key])
                    common = len(user_values & major_values)
                    score += common * weights.get(key, 1.0)

            return score
        except Exception as e:
            print(f"⚠️ خطأ في حساب التوافق: {str(e)}")
            return 0.0

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        majors = self.load_majors()
        if not majors:
            dispatcher.utter_message(text="⚠️ تعذر تحميل بيانات التخصصات، الرجاء المحاولة لاحقاً")
            return []

    
        best_major = None
        highest_score = 0
        
        for major in majors:
            score = self.calculate_match_score(major, tracker)
            if score > highest_score:
                highest_score = score
                best_major = major

        if not best_major:
            dispatcher.utter_message(text="بناءً على اهتماماتك ومهاراتك وأسلوبك في التعلّم والتفكير، نرى أن تخصص ادارة الأعمال هو الأنسب لك!")

        
        major_name = best_major.get("name", "هذا التخصص")
        response = (
            f"بناءً على اهتماماتك ومهاراتك وأسلوبك في التعلّم والتفكير، "
            f"نرى أن تخصص {major_name} هو الأنسب لك!"
        )

        dispatcher.utter_message(text=response)
        
    
    
        return [SlotSet("recommended_major", major_name)]
#########db.departments
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import mysql.connector

class ActionAskAboutDepartments(Action):
    def name(self) -> Text:
        return "action_ask_about_departments"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        try:
            
            connection = mysql.connector.connect(
                host="localhost",
                user="root",
                password="",
                database="academy",
                auth_plugin='mysql_native_password'
            )
            
            cursor = connection.cursor()
            
    
            query = "SELECT name_department FROM departments"
            cursor.execute(query)
            
        
            departments = cursor.fetchall()
            
            if departments:
                response = "📚 الأقسام المتاحة في المعهد:\n\n" + "\n".join([f"• {dept[0]}" for dept in departments])
            else:
                response = "⚠️ لا توجد أقسام مسجلة حالياً."
            
            dispatcher.utter_message(text=response)
            
        except mysql.connector.Error as err:
            error_msg = f"🔴 حدث خطأ تقني: {err}"
            print(error_msg)  
            dispatcher.utter_message(text="عذراً، حدث خطأ في جلب البيانات. يرجى المحاولة لاحقاً")
            
        finally:
            
            if 'connection' in locals() and connection.is_connected():
                cursor.close()
                connection.close()
        
        return []
    
#####db.sp
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import mysql.connector

class ActionAskAboutSpecializations(Action):
    def name(self) -> Text:
        return "action_ask_about_specializations"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        try:
            # 1. إنشاء الاتصال (بنفس إعدادات الاتصال الناجحة)
            connection = mysql.connector.connect(
                host="localhost",
                user="root",
                password="",
                database="academy",
                auth_plugin='mysql_native_password'
            )
            
            cursor = connection.cursor(dictionary=True)  # استخدام dictionary=True لنتائج بأسماء الأعمدة
            
            # 2. استعلام متقدم لجلب الأقسام مع تخصصاتها
            query = """
            SELECT 
                d.name_department AS department,
                GROUP_CONCAT(s.spec_name SEPARATOR ' • ') AS specializations
            FROM 
                departments d
            LEFT JOIN 
                specializations s ON d.id = s.dept_id
            GROUP BY 
                d.name_department
            """
            cursor.execute(query)
            
            # 3. معالجة النتائج
            results = cursor.fetchall()
            
            if results:
                response = "📚 التخصصات المتاحة حسب الأقسام:\n\n"
                for row in results:
                    specs = row['specializations'] if row['specializations'] else "لا توجد تخصصات مسجلة"
                    response += f"🏛 **{row['department']}**:\n{specs}\n\n"
            else:
                response = "⚠️ لا توجد تخصصات مسجلة في أي قسم."
            
            dispatcher.utter_message(text=response)
            
        except mysql.connector.Error as err:
            # 4. معالجة الأخطاء بنفس الأسلوب
            error_msg = f"🔴 خطأ في قاعدة البيانات: {err}"
            print(error_msg)  
            dispatcher.utter_message(text="عذراً، حدث خطأ تقني أثناء جلب التخصصات. يرجى المحاولة لاحقاً")
            
        finally:
            # 5. إغلاق الاتصال بنفس الطريقة
            if 'connection' in locals() and connection.is_connected():
                cursor.close()
                connection.close()
        
        return []
######db.admission      
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import mysql.connector

class ActionWhatAdmission(Action):
    def name(self) -> Text:
        return "action_what_admission"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        try:
            # الاتصال بقاعدة البيانات
            db = mysql.connector.connect(
                host="localhost",
                user="root",
                password="",
                database="academy",
                auth_plugin='mysql_native_password'
            )
            
            cursor = db.cursor(dictionary=True)
            
            # استعلام المفاضلة
            query = """
            SELECT 
                specialization_name,
                literary_score,
                scientific_score,
                commercial_score,
                industrial_it_score,
                informatics_score,
                arts_score
            FROM admission
            """
            cursor.execute(query)
            results = cursor.fetchall()
            
            if results:
                response = "🎯 مفاضلة القبول في التخصصات:\n\n"
                for row in results:
                    specs = []
                    if row['literary_score']: specs.append(f"أدبي: {row['literary_score']}")
                    if row['scientific_score']: specs.append(f"علمي: {row['scientific_score']}")
                    if row['commercial_score']: specs.append(f"تجاري: {row['commercial_score']}")
                    if row['industrial_it_score']: specs.append(f"صناعي: {row['industrial_it_score']}")
                    if row['informatics_score']: specs.append(f"معلوماتية: {row['informatics_score']}")
                    if row['arts_score']: specs.append(f"فنون: {row['arts_score']}")
                    
                    if specs:  # فقط إذا كان هناك علامات
                        response += f"🏷 {row['specialization_name']}:\n   - " + "\n   - ".join(specs) + "\n\n"
                
                dispatcher.utter_message(text=response)
            else:
                dispatcher.utter_message(text="⚠️ لا توجد بيانات مفاضلة متاحة حالياً")
                
        except Exception as e:
            dispatcher.utter_message(text="⛔ حدث خطأ في جلب بيانات المفاضلة")
            print(f"Error: {str(e)}")
        finally:
            if db.is_connected():
                cursor.close()
                db.close()
        return []