from __future__ import annotations

from typing import Any


def visual_palette(seed: int) -> tuple[str, str, str]:
    palettes = (
        ("#8ba87a", "#d4a574", "#c47a5a"),
        ("#9a7b56", "#e8c089", "#8ba87a"),
        ("#a67c6a", "#b89164", "#6f7f64"),
        ("#c47a5a", "#c49a6c", "#a67c6a"),
    )
    return palettes[seed % len(palettes)]


def demo_samples(language: str = "en") -> list[dict[str, Any]]:
    return chinese_demo_samples() if language == "zh" else english_demo_samples()


def english_reflections(emotion: str, waking: str, elements: str, context: str, association: str) -> dict[str, str]:
    return {
        "strongest_emotion": emotion,
        "waking_feeling": waking,
        "important_elements": elements,
        "real_life_context": context,
        "personal_association": association,
    }


def english_analysis(
    *,
    emotional_tone: str,
    symbols: list[str],
    themes: list[str],
    summary: str,
    dream_details: list[str],
    core_emotion: str,
    real_life_links: list[str],
    title: str,
    interpretation: str,
    dream_evidence: str,
    real_life_connection: str,
    verification_question: str,
    real_life_questions: list[str],
    verification_prompts: list[str],
) -> dict[str, Any]:
    return {
        "analysis_version": 2,
        "emotional_tone": emotional_tone,
        "symbols": symbols,
        "themes": themes,
        "summary": summary,
        "confidence": 0.82,
        "dream_details": dream_details,
        "core_emotion": core_emotion,
        "important_elements": symbols,
        "real_life_links": real_life_links,
        "personal_associations": [real_life_connection],
        "possible_interpretations": [
            {
                "title": title,
                "interpretation": interpretation,
                "dream_evidence": dream_evidence,
                "real_life_connection": real_life_connection,
                "verification_question": verification_question,
            }
        ],
        "real_life_questions": real_life_questions,
        "verification_prompts": verification_prompts,
    }


def english_demo_samples() -> list[dict[str, Any]]:
    return [
        {
            "content": "I kept walking through a quiet subway station, but every exit led back to the same platform.",
            "reflections": english_reflections(
                "uneasy curiosity",
                "I woke up wanting a real exit.",
                "subway station, repeating platform, exit signs",
                "I have been comparing several life options.",
                "It reminds me of revisiting the same decision from different angles.",
            ),
            "analysis": english_analysis(
                emotional_tone="uneasy but curious",
                symbols=["subway station", "repeating platform", "exit"],
                themes=["transition", "uncertainty"],
                summary="A transition dream where every route returns to the same unresolved question.",
                dream_details=["The station feels quiet rather than dangerous.", "Every exit leads back to the same platform."],
                core_emotion="A mix of curiosity and low-grade frustration.",
                real_life_links=["You may be circling a decision without finding a satisfying next step."],
                title="A decision loop",
                interpretation="The repeating platform may reflect revisiting the same choice from different angles.",
                dream_evidence="Each exit returns to the same place.",
                real_life_connection="This can map to a decision that has no perfect option yet.",
                verification_question="Which real choice keeps bringing you back to the same concern?",
                real_life_questions=["What decision feels circular rather than impossible?"],
                verification_prompts=["Write down the choices you keep comparing and what each one costs."],
            ),
        },
        {
            "content": "A blue door appeared under the sea. I could breathe, but I waited before opening it.",
            "reflections": english_reflections(
                "wonder with caution",
                "I woke up calm but alert.",
                "blue door, sea, breathing underwater",
                "A new project feels exciting and heavy.",
                "The door feels like a chance I do not want to rush.",
            ),
            "analysis": english_analysis(
                emotional_tone="wonder with caution",
                symbols=["blue door", "sea", "waiting"],
                themes=["threshold", "exploration"],
                summary="A threshold dream about a possible opening that still asks for emotional readiness.",
                dream_details=["The door is under the sea.", "You can breathe, but you do not rush."],
                core_emotion="Interest held back by caution.",
                real_life_links=["A promising opportunity may feel real but not fully safe yet."],
                title="Approaching an opportunity carefully",
                interpretation="The blue door may mark a new option, while the sea adds emotional depth.",
                dream_evidence="You can breathe, yet you wait.",
                real_life_connection="This may echo a project or relationship that needs pacing.",
                verification_question="Where are you interested but not ready to commit?",
                real_life_questions=["What opening needs patience rather than force?"],
                verification_prompts=["Notice whether excitement or fear is leading the delay."],
            ),
        },
        {
            "content": "I found an old library where the books rearranged themselves whenever I touched the shelves.",
            "reflections": english_reflections(
                "fascinated",
                "I wanted to remember the layout.",
                "old library, moving shelves, rearranging books",
                "I have been rebuilding my notes and writing system.",
                "It feels like a map of memory that changes when I use it.",
            ),
            "analysis": english_analysis(
                emotional_tone="fascinated and slightly overwhelmed",
                symbols=["old library", "moving shelves", "rearranging books"],
                themes=["memory", "knowledge", "change"],
                summary="A knowledge dream where memory keeps reorganizing itself as you interact with it.",
                dream_details=["Books rearrange when touched.", "The library feels old and alive."],
                core_emotion="The pleasure of discovery mixed with too much information.",
                real_life_links=["You may be reorganizing how you understand a topic or period of life."],
                title="A changing knowledge map",
                interpretation="The library may reflect a personal knowledge system that evolves as you use it.",
                dream_evidence="The books move only when you touch the shelves.",
                real_life_connection="This may map to learning, writing, or rebuilding your notes.",
                verification_question="What knowledge area changes shape whenever you engage with it?",
                real_life_questions=["What system are you trying to reorganize without losing yourself in it?"],
                verification_prompts=["Pick one area of knowledge and name the pattern that keeps shifting."],
            ),
        },
    ]


def zh_reflections(emotion: str, waking: str, elements: str, context: str, association: str) -> dict[str, str]:
    return {
        "strongest_emotion": emotion,
        "waking_feeling": waking,
        "important_elements": elements,
        "real_life_context": context,
        "personal_association": association,
    }


def zh_analysis(
    *,
    emotional_tone: str,
    symbols: list[str],
    themes: list[str],
    summary: str,
    dream_details: list[str],
    core_emotion: str,
    real_life_links: list[str],
    title: str,
    interpretation: str,
    dream_evidence: str,
    real_life_connection: str,
    verification_question: str,
) -> dict[str, Any]:
    return {
        "analysis_version": 2,
        "emotional_tone": emotional_tone,
        "symbols": symbols,
        "themes": themes,
        "summary": summary,
        "confidence": 0.84,
        "dream_details": dream_details,
        "core_emotion": core_emotion,
        "important_elements": symbols,
        "real_life_links": real_life_links,
        "personal_associations": [real_life_connection],
        "possible_interpretations": [
            {
                "title": title,
                "interpretation": interpretation,
                "dream_evidence": dream_evidence,
                "real_life_connection": real_life_connection,
                "verification_question": verification_question,
            }
        ],
        "real_life_questions": ["这个梦最像现实里的哪一个反复出现的问题？"],
        "verification_prompts": ["把梦里的核心情绪和最近一周最反复的压力放在一起比较。"],
    }


def chinese_demo_samples() -> list[dict[str, Any]]:
    return [
        {
            "content": "我梦见自己在夜里的车站等车，广播一直说下一班马上到，但站台始终空着。",
            "reflections": zh_reflections("期待又焦虑", "醒来后觉得有点悬着", "夜里车站、广播、空站台", "最近在等一个项目结果", "像是在等一个迟迟不给答案的消息"),
            "analysis": zh_analysis(
                emotional_tone="期待中带着焦虑",
                symbols=["夜里车站", "广播", "空站台"],
                themes=["等待", "不确定"],
                summary="这是一个关于等待反馈的梦，重点不在车是否出现，而在你被悬置的状态。",
                dream_details=["广播反复说车快到了。", "站台始终没有人也没有车。"],
                core_emotion="想继续相信，但身体已经开始不安。",
                real_life_links=["现实中可能有一个结果、回复或机会还没有落地。"],
                title="被延长的等待",
                interpretation="空站台可能反映一种没有控制权的等待。",
                dream_evidence="广播给出承诺，但环境没有变化。",
                real_life_connection="这像是你最近在等项目结果时的心理状态。",
                verification_question="最近哪个等待让你既期待又无法安排下一步？",
            ),
        },
        {
            "content": "我走进一间旧教室，黑板上写满我看不懂的公式，但桌上放着一杯温热的茶。",
            "reflections": zh_reflections("紧张但被安抚", "醒来后记得那杯茶", "旧教室、黑板公式、热茶", "最近在学一个难主题", "茶像是提醒我可以慢一点"),
            "analysis": zh_analysis(
                emotional_tone="压力中有安定感",
                symbols=["旧教室", "公式", "热茶"],
                themes=["学习", "自我安抚"],
                summary="这个梦把学习压力和照顾自己的信号放在同一个空间里。",
                dream_details=["黑板内容难以理解。", "桌上的茶是温热的。"],
                core_emotion="怕跟不上，但仍然能找到一点支持。",
                real_life_links=["现实中你可能正在面对一个需要耐心拆解的新主题。"],
                title="困难旁边的支持",
                interpretation="公式代表复杂任务，热茶代表可用的缓冲和照顾。",
                dream_evidence="梦里同时出现难题和温热的茶。",
                real_life_connection="这可能对应你最近学习或工作里的压力。",
                verification_question="你能不能给当前难题加一个更温和的节奏？",
            ),
        },
        {
            "content": "我在雨后的巷子里找伞，最后发现伞其实一直背在身后。",
            "reflections": zh_reflections("着急后放松", "醒来后觉得有点好笑", "雨后巷子、伞、背包", "最近总担心准备不够", "像是我其实已经有工具了"),
            "analysis": zh_analysis(
                emotional_tone="从紧张转向释然",
                symbols=["雨后巷子", "伞", "背包"],
                themes=["准备", "自信"],
                summary="这个梦像是在提醒你：某些资源已经在身上，只是焦虑让你暂时看不见。",
                dream_details=["你一直在找伞。", "伞最后被发现就在背后。"],
                core_emotion="担心不足，随后发现自己并非毫无准备。",
                real_life_links=["现实中你可能低估了已有经验或工具。"],
                title="已经带着的工具",
                interpretation="伞可能象征你以为缺失、其实已经拥有的保护。",
                dream_evidence="寻找的东西一直在你身后。",
                real_life_connection="这可能对应你最近对准备程度的担心。",
                verification_question="哪件事你其实已经准备得比自己以为的更多？",
            ),
        },
        {
            "content": "我在海边看到一座玻璃桥，桥下有很深的水，但桥面很稳。",
            "reflections": zh_reflections("害怕又想过去", "醒来后还记得桥很透明", "海、玻璃桥、深水", "最近在考虑公开一个作品", "桥像是曝光感，也像通往下一步"),
            "analysis": zh_analysis(
                emotional_tone="害怕暴露但想前进",
                symbols=["玻璃桥", "深水", "海边"],
                themes=["跨越", "公开"],
                summary="这个梦把前进和被看见的紧张放在一起，桥稳说明风险可能比感觉中更可承受。",
                dream_details=["桥是透明的。", "水很深但桥面稳定。"],
                core_emotion="想迈过去，但害怕被暴露或失足。",
                real_life_links=["现实中可能有一个需要公开、展示或提交的动作。"],
                title="可承受的曝光",
                interpretation="玻璃桥可能代表一个透明、被看见但仍然可靠的过渡。",
                dream_evidence="桥下很深，桥面却很稳。",
                real_life_connection="这像是你对公开作品的兴奋和紧张。",
                verification_question="你害怕的是桥不稳，还是害怕别人看到你在桥上？",
            ),
        },
        {
            "content": "我打开家里的抽屉，里面不是杂物，而是一排排发光的小标签。",
            "reflections": zh_reflections("惊讶和清晰", "醒来后想整理东西", "抽屉、发光标签、家", "最近在整理笔记和计划", "标签像是给混乱重新命名"),
            "analysis": zh_analysis(
                emotional_tone="混乱后出现清晰感",
                symbols=["抽屉", "发光标签", "家"],
                themes=["整理", "命名"],
                summary="这个梦像是一个整理信号：不是要增加更多东西，而是把已有内容重新命名。",
                dream_details=["抽屉里没有杂物。", "标签发着光并排放着。"],
                core_emotion="从预期混乱转向可理解的秩序。",
                real_life_links=["现实中你可能正在给笔记、项目或计划重新分类。"],
                title="给混乱命名",
                interpretation="发光标签可能代表能让现有材料变清楚的分类方式。",
                dream_evidence="你打开抽屉后看到的是标签而不是杂物。",
                real_life_connection="这可能对应你最近整理知识系统的需求。",
                verification_question="哪一堆材料只需要重新命名，而不是继续扩充？",
            ),
        },
    ]
