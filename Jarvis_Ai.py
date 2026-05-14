#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JARVIS AI ULTIMATE – To'liq birlashtirilgan tizim
- Jarvis AI: shaxsiy yordamchi (vaqt, ob-havo, fayl, eslatma, seyf, xotira, o'rganish, refleksiya)
- Habitat AI qobiliyatlari: Habitat tilida kod yozish, loyiha yaratish, xavfsizlik tahlili
- Habitat AI alohida emas, hammasi Jarvis ichida
Hech qanday tayyor AI API ishlatilmagan - sof Python
"""

import os
import re
import json
import time
import shutil
import datetime
import random
import hashlib
from pathlib import Path
from collections import deque
from typing import Dict, List, Optional, Tuple, Any

# ============================================================================
# 1. JARVIS CORE MODULLARI (Xotira, Kontekst, O'rganish)
# ============================================================================

class VectorMemory:
    """Vektor asosidagi xotira (numpy o'rniga sof Python)"""
    def __init__(self, dim=384, max_items=5000, storage_path="jarvis_memory.json"):
        self.dim = dim
        self.max_items = max_items
        self.storage_path = storage_path
        self.vectors = []
        self.metadata = []
        self._load()
    
    def _text_to_vector(self, text):
        vec = [0.0] * self.dim
        for i, ch in enumerate(text.encode('utf-8')):
            idx = i % self.dim
            vec[idx] += (ch / 255.0)
        norm = sum(v*v for v in vec)**0.5
        if norm > 0:
            vec = [v/norm for v in vec]
        return vec
    
    def add(self, query, response):
        vec = self._text_to_vector(query + " " + response)
        self.vectors.append(vec)
        self.metadata.append({"query": query, "response": response, "timestamp": time.time()})
        if len(self.vectors) > self.max_items:
            self.vectors.pop(0)
            self.metadata.pop(0)
        self._save()
    
    def recall(self, query, threshold=0.65):
        if not self.vectors:
            return None
        q_vec = self._text_to_vector(query)
        best_sim = -1
        best_idx = -1
        for i, v in enumerate(self.vectors):
            sim = sum(q_vec[j]*v[j] for j in range(self.dim))
            if sim > best_sim:
                best_sim = sim
                best_idx = i
        if best_sim >= threshold:
            return self.metadata[best_idx]["response"]
        return None
    
    def _save(self):
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump({"vectors": self.vectors, "metadata": self.metadata}, f)
    
    def _load(self):
        if os.path.exists(self.storage_path):
            with open(self.storage_path, "r") as f:
                data = json.load(f)
                self.vectors = data.get("vectors", [])
                self.metadata = data.get("metadata", [])


class ConversationContext:
    def __init__(self, max_history=10):
        self.history = deque(maxlen=max_history)
        self.current_topic = None
    
    def add(self, role, content):
        self.history.append({"role": role, "content": content})
        if role == "user":
            words = content.lower().split()
            if words:
                self.current_topic = " ".join(words[:3])
    
    def get_topic(self):
        return self.current_topic


class SelfLearningEngine:
    def __init__(self, knowledge_path="universal_knowledge.json"):
        self.knowledge_path = knowledge_path
        self.cache = {}
        self._load()
    
    def _load(self):
        if os.path.exists(self.knowledge_path):
            with open(self.knowledge_path, "r") as f:
                data = json.load(f)
                self.cache = data.get("learned_commands", {})
    
    def _save(self):
        with open(self.knowledge_path, "w", encoding="utf-8") as f:
            json.dump({"learned_commands": self.cache}, f, ensure_ascii=False, indent=2)
    
    def learn(self, query):
        query_lower = query.lower().strip()
        if query_lower in self.cache:
            return self.cache[query_lower]
        # Internet qidiruvi (realda requests kerak)
        try:
            import requests
            from bs4 import BeautifulSoup
            from urllib.parse import quote_plus
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
            soup = BeautifulSoup(resp.text, "html.parser")
            snippet = soup.select_one(".result__snippet")
            answer = snippet.get_text(strip=True) if snippet else f"{query} haqida ma'lumot topilmadi."
        except:
            answer = f"Kechirasiz, '{query}' bo'yicha internetdan javob topa olmadim."
        self.cache[query_lower] = answer
        self._save()
        return answer
      # ============================================================================
# 2. HABITAT QOBILIYATLARI (Jarvis ichiga integratsiya)
# ============================================================================

class HabitatSecurityAnalyzer:
    @staticmethod
    def analyze(code: str) -> List[Dict]:
        issues = []
        patterns = [
            (r'eval\s*\(', "Xavfli: eval() ishlatilgan", "HIGH"),
            (r'exec\s*\(', "Xavfli: exec() ishlatilgan", "HIGH"),
            (r'password\s*=\s*["\'][^"\']+["\']', "Parol ochiq matnda", "MEDIUM"),
            (r'\+.*?sql', "SQL injection xavfi", "HIGH"),
            (r'pickle\.loads', "Xavfli deserializatsiya", "MEDIUM")
        ]
        for pattern, msg, sev in patterns:
            if re.search(pattern, code, re.IGNORECASE):
                issues.append({"severity": sev, "message": msg, "pattern": pattern})
        return issues


class HabitatProjectGenerator:
    TEMPLATES = {
        "web_app": {
            "src/main.hab": "import web.server\n\nfunc main() {\n    web.server.run(8080)\n    print('Server ishga tushdi')\n}",
            "config.json": '{"port": 8080, "debug": true}'
        },
        "cli_tool": {
            "src/main.hab": "import system.args\n\nfunc main() {\n    let args = system.args.get()\n    print('Habitat CLI tool')\n    print(args)\n}",
            "README.md": "# CLI Tool\n\nHabitat tilida yozilgan buyruq qatori vositasi"
        },
        "ai_agent": {
            "src/agent.hab": "import ai.core\n\nclass Agent {\n    func think(input: string) -> string {\n        return 'Men Habitat AI agentman'\n    }\n}",
            "requirements.hab": "ai.core >= 1.0"
        }
    }
    
    @classmethod
    def create(cls, name, typ, output_dir="./jarvis_projects"):
        if typ not in cls.TEMPLATES:
            return {"error": f"Noma'lum tur: {typ}. Mavjud: {list(cls.TEMPLATES.keys())}"}
        base = Path(output_dir) / name
        base.mkdir(parents=True, exist_ok=True)
        (base / "src").mkdir(exist_ok=True)
        files = []
        for fname, content in cls.TEMPLATES[typ].items():
            fpath = base / fname
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(content, encoding="utf-8")
            files.append(str(fpath))
        (base / "Habitat.toml").write_text(f'[package]\nname="{name}"\ntype="{typ}"\nversion="0.1.0"', encoding="utf-8")
        return {"success": True, "path": str(base), "files": files}


class HabitatCodeGenerator:
    @staticmethod
    def variable(name, value, var_type=None):
        type_ann = f":{var_type}" if var_type else ""
        val = f'"{value}"' if isinstance(value, str) else str(value)
        return f"let {name}{type_ann} = {val}"
    
    @staticmethod
    def function(name, params, return_type, body):
        p_str = ", ".join([f"{p[0]}:{p[1]}" for p in params])
        ret = f"->{return_type}" if return_type else ""
        return f"func {name}({p_str}){ret} {{\n    {body}\n}}"
    
    @staticmethod
    def class_def(name, fields, methods):
        f_str = "\n    ".join([f"let {f[0]}:{f[1]}" for f in fields])
        m_str = "\n\n    ".join(methods)
        return f"class {name} {{\n    {f_str}\n\n    {m_str}\n}}"
    
    @staticmethod
    def if_stmt(cond, then_body, else_body=None):
        res = f"if {cond} {{\n    {then_body}\n}}"
        if else_body:
            res += f" else {{\n    {else_body}\n}}"
        return res
    
    @staticmethod
    def for_loop(var, iterable, body):
        return f"for {var} in {iterable} {{\n    {body}\n}}"
    
    @staticmethod
    def async_func(name, params, return_type, body):
        p_str = ", ".join([f"{p[0]}:{p[1]}" for p in params])
        ret = f"->{return_type}" if return_type else ""
        return f"async func {name}({p_str}){ret} {{\n    {body}\n}}"
    
    @staticmethod
    def import_stmt(module):
        return f"import {module}"
      # ============================================================================
# 3. COGNITIVE MODULLAR (Reflection, Self-Evaluation)
# ============================================================================

class SelfEvaluator:
    def __init__(self):
        self.feedback_history = []
    
    def evaluate(self, query, response):
        score = 5.0
        if len(response) < 10:
            score -= 1
        if len(response) > 500:
            score -= 0.5
        if "tushunmadim" in response.lower():
            score -= 2
        if "bilib oldim" in response.lower():
            score += 1
        if "```" in response:
            score += 0.5  # kod bergani yaxshi
        score = max(0, min(10, score))
        self.feedback_history.append({"query": query, "score": score, "timestamp": time.time()})
        return {"score": round(score, 1), "verdict": "yaxshi" if score >= 7 else "o'rtacha" if score >= 4 else "yomon"}
    
    def avg_score(self):
        if not self.feedback_history:
            return 0
        return sum(h["score"] for h in self.feedback_history) / len(self.feedback_history)


class ReflectionEngine:
    def __init__(self):
        self.reflections = []
        self.lessons = {}
    
    def reflect(self, action, outcome, success):
        lesson = f"{action} – muvaffaqiyatli" if success else f"{action} – muvaffaqiyatsiz, sabab: {outcome[:50]}"
        self.reflections.append({
            "action": action, 
            "outcome": outcome[:100], 
            "success": success, 
            "lesson": lesson,
            "timestamp": time.time()
        })
        # Saboqlarni statistikasi
        if lesson in self.lessons:
            self.lessons[lesson] += 1
        else:
            self.lessons[lesson] = 1
        return lesson
    
    def summary(self):
        if not self.reflections:
            return "Hali refleksiya yo'q"
        # Eng ko'p takrorlangan saboq
        if self.lessons:
            best_lesson = max(self.lessons.items(), key=lambda x: x[1])
            return f"Eng muhim saboq: {best_lesson[0]} ({best_lesson[1]} marta)"
        return f"So'nggi refleksiya: {self.reflections[-1]['lesson']}"
    
    def get_best_practice(self, action_prefix=""):
        if not self.lessons:
            return None
        filtered = {k:v for k,v in self.lessons.items() if action_prefix in k}
        if filtered:
            return max(filtered.items(), key=lambda x: x[1])[0]
        return max(self.lessons.items(), key=lambda x: x[1])[0]
      # ============================================================================
# 4. JARVIS ULTIMATE – ASOSIY TIZIM (1/2)
# ============================================================================

class JarvisUltimate:
    def __init__(self):
        self.name = "Jarvis AI Ultimate"
        self.version = "3.0.0"
        
        # Jarvis modullari
        self.memory = VectorMemory()
        self.context = ConversationContext()
        self.learner = SelfLearningEngine()
        self.evaluator = SelfEvaluator()
        self.reflector = ReflectionEngine()
        
        # Habitat qobiliyatlari (integratsiya)
        self.habitat_security = HabitatSecurityAnalyzer()
        self.habitat_project_gen = HabitatProjectGenerator()
        self.habitat_code_gen = HabitatCodeGenerator()
        
        self.start_time = time.time()
        
        # Buyruq handlerlari
        self.handlers = {
            "salom": self.greet,
            "vaqt": self.get_time,
            "sana": self.get_date,
            "ob-havo": self.weather,
            "yangiliklar": self.news,
            "eslatma": self.reminder,
            "fayl": self.file_manager,
            "seyf": self.vault,
            "tahlil": self.analyze,
            "yordam": self.help,
            "chiqish": self.exit,
            "status": self.status,
            "habitat kod": self.habitat_generate_code,
            "habitat loyiha": self.habitat_create_project,
            "habitat tahlil": self.habitat_analyze_code,
        }
    
    # ========== Jarvis asosiy funksiyalari ==========
    def greet(self, text):
        hour = datetime.datetime.now().hour
        greeting = "Xayrli tong" if hour < 12 else "Xayrli kun"
        return f"{greeting}, janob! Jarvis AI Ultimate xizmatingizda."
    
    def get_time(self, text):
        return datetime.datetime.now().strftime("Hozir %H:%M:%S")
    
    def get_date(self, text):
        return datetime.datetime.now().strftime("Bugun %d-%B, %Y")
    
    def weather(self, text):
        return "Toshkentda havo 22°C, ochiq. (Simulyatsiya, real API uchun sozlang)"
    
    def news(self, text):
        return "So'nggi yangiliklar: Jarvis AI Ultimate versiyasi chiqdi."
    
    def reminder(self, text):
        return "Eslatma qo'shildi (oddiy simulyatsiya). To'liq funksiya uchun scheduler qo'shing."
    
    def file_manager(self, text):
        return "Fayl boshqaruvi: 'fayllarni ko'rsat', 'fayl yarat', 'faylni o'chir' qo'llab-quvvatlanadi."
    
    def vault(self, text):
        return "Maxfiy seyf: 'seyfga qo'y kalit qiymat', 'seyfdan ol kalit'"
    
    def analyze(self, text):
        return "Statistik tahlil moduli. JSON fayllarni tahlil qiladi."
    
    def help(self, text):
        return """
Jarvis AI Ultimate buyruqlari:

【Umumiy】
- salom, vaqt, sana, ob-havo, yangiliklar
- eslatma, fayl, seyf, tahlil, yordam, chiqish, status

【Habitat qobiliyatlari (Jarvis ichida)】
- habitat kod variable name <nomi> value <qiymat>
- habitat kod function
- habitat kod class
- habitat kod if / for
- habitat loyiha <nomi> <web_app|cli_tool|ai_agent>
- habitat tahlil ```habitat ... ```
"""
    
    def exit(self, text):
        return "Tizim tugatilmoqda. Xayr, janob!"
    
    def status(self, text):
        avg_score = self.evaluator.avg_score()
        return f"""
🤖 {self.name} v{self.version}
- Vektor xotira: {len(self.memory.vectors)} ta eslab qolingan
- O'rganilgan bilimlar: {len(self.learner.cache)} ta
- O'rtacha baho: {avg_score:.1f}/10
- Refleksiyalar: {len(self.reflector.reflections)} ta
- {self.reflector.summary()}

"""
          # ========== Habitat qobiliyatlari (integratsiya) ==========
    def habitat_generate_code(self, text):
        prompt = text.replace("habitat kod", "").strip()
        if not prompt:
            return "Iltimos, spetsifikatsiya bering. Misol: 'habitat kod variable name age value 25'"
        
        if "variable" in prompt:
            name_match = re.search(r'name\s+(\w+)', prompt)
            val_match = re.search(r'value\s+(\w+)', prompt)
            if name_match and val_match:
                name, value = name_match.group(1), val_match.group(1)
                var_type = "int" if value.isdigit() else "string"
                code = self.habitat_code_gen.variable(name, value, var_type)
                return f"```habitat\n{code}\n```"
        elif "function" in prompt:
            code = self.habitat_code_gen.function("myFunc", [("a","int"),("b","int")], "int", "return a + b")
            return f"```habitat\n{code}\n```"
        elif "class" in prompt:
            code = self.habitat_code_gen.class_def("MyClass", [("value","int")], ["func get() -> int { return this.value }"])
            return f"```habitat\n{code}\n```"
        elif "if" in prompt:
            code = self.habitat_code_gen.if_stmt("x > 0", 'print("positive")', 'print("negative")')
            return f"```habitat\n{code}\n```"
        elif "for" in prompt:
            code = self.habitat_code_gen.for_loop("i", "1..10", 'print(i)')
            return f"```habitat\n{code}\n```"
        else:
            return "Tushunarsiz. Misol: 'habitat kod variable name x value 10'"
    
    def habitat_create_project(self, text):
        parts = text.replace("habitat loyiha", "").strip().split()
        if len(parts) < 2:
            return "Format: habitat loyiha <nomi> <turi> (web_app, cli_tool, ai_agent)"
        name, typ = parts[0], parts[1]
        result = self.habitat_project_gen.create(name, typ)
        if result.get("success"):
            return f"✅ Loyiha yaratildi: {result['path']}\nFayllar: {', '.join(result['files'])}"
        else:
            return f"❌ Xatolik: {result.get('error')}"
    
    def habitat_analyze_code(self, text):
        code_match = re.search(r'```habitat(.*?)```', text, re.DOTALL)
        if not code_match:
            code = text.replace("habitat tahlil", "").strip()
            if not code:
                return "Kodni ```habitat ... ``` blokiga yozing."
        else:
            code = code_match.group(1)
        issues = self.habitat_security.analyze(code)
        if issues:
            return "Xavfsizlik muammolari:\n" + "\n".join([f"- [{i['severity']}] {i['message']}" for i in issues])
        else:
            return "Xavfsizlik tekshiruvidan o'tdi. Muammo topilmadi."
    
    # ========== Asosiy ishlov beruvchi ==========
    def process(self, user_input: str) -> str:
        user_input = user_input.strip()
        if not user_input:
            return "Janob, buyruq bering."
        
        self.context.add("user", user_input)
        
        # Vektor xotira
        recalled = self.memory.recall(user_input, threshold=0.75)
        if recalled:
            self.context.add("jarvis", recalled)
            return recalled
        
        # Buyruqni aniqlash
        input_lower = user_input.lower()
        
        # Habitat buyruqlari (endi Jarvis ichida)
        if input_lower.startswith("habitat"):
            for key in self.handlers:
                if key.startswith("habitat") and input_lower.startswith(key):
                    response = self.handlers[key](user_input)
                    self.context.add("jarvis", response)
                    self.memory.add(user_input, response)
                    eval_res = self.evaluator.evaluate(user_input, response)
                    self.reflector.reflect(user_input, response, eval_res["score"] >= 5)
                    return response
        
        # Oddiy Jarvis buyruqlari
        for key in self.handlers:
            if key in input_lower and not key.startswith("habitat") and key != "status":
                response = self.handlers[key](user_input)
                self.context.add("jarvis", response)
                self.memory.add(user_input, response)
                eval_res = self.evaluator.evaluate(user_input, response)
                self.reflector.reflect(user_input, response, eval_res["score"] >= 5)
                return response
        
        if "status" in input_lower:
            return self.status(user_input)
        
        # Hech narsa topilmasa – o'rganish
        answer = self.learner.learn(user_input)
        if answer and "topilmadi" not in answer:
            self.context.add("jarvis", answer)
            self.memory.add(user_input, answer)
            eval_res = self.evaluator.evaluate(user_input, answer)
            self.reflector.reflect(user_input, answer, eval_res["score"] >= 5)
            return f"Janob, men buni bilib oldim: {answer}"
        else:
            return f"Kechirasiz, janob. '{user_input}' buyrug'ini tushunmadim. 'yordam' deb yozing."


# ============================================================================
# 5. ISHGA TUSHIRISH
# ============================================================================

if __name__ == "__main__":
    jarvis = JarvisUltimate()
    print("=" * 60)
    print(f"🤖 {jarvis.name} v{jarvis.version} ishga tushdi.")
    print("Habitat AI qobiliyatlari Jarvis AI ga o'tkazildi. Habitat AI alohida olib tashlandi.")
    print("Buyruqlar: 'yordam', 'habitat kod ...', 'habitat loyiha ...', 'status'")
    print("'chiqish' -> tugatish")
    print("=" * 60)
    
    while True:
        try:
            cmd = input("\n[Siz] ").strip()
            if cmd.lower() in ["chiqish", "exit", "quit"]:
                print(jarvis.process("chiqish"))
                break
            if not cmd:
                continue
            response = jarvis.process(cmd)
            print(f"\n[Jarvis] {response}")
        except KeyboardInterrupt:
            print("\nTizim to'xtatildi.")
            break
        except Exception as e:
            print(f"Xatolik: {e}")
          
