#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from client.senior import captcha_get, captcha_submit, category_get, question_get, question_result, question_submit
from tools.logger import logger
from tools.LLM.deepseek import DeepSeekAPI
from tools.LLM.custom import CustomAPI
from tools.LLM.pipeline import decide
from config.config import model_choice
from time import perf_counter, sleep

PASS_SCORE = 60


class AnswerStats:
    """本轮答题统计。正确率 = 正确 / (正确 + 失败)。"""

    def __init__(self):
        self.records = []
        self.score = 0
        self.score_known = False
        self.finished = False
        self.stopped = False

    def add(self, question_num, elapsed_s, correct):
        self.records.append({
            "question_num": question_num,
            "elapsed_s": elapsed_s,
            "correct": correct,
        })

    def snapshot(self):
        correct_count = sum(1 for item in self.records if item["correct"] is True)
        failed_count = sum(1 for item in self.records if item["correct"] is False)
        judged = correct_count + failed_count
        accuracy = (correct_count / judged) if judged else None
        times = [item["elapsed_s"] for item in self.records]
        last = self.records[-1] if self.records else None
        if self.finished and self.score >= PASS_SCORE:
            status = "已通过"
        elif self.score >= PASS_SCORE:
            status = "已达标"
        elif self.finished:
            status = "未通过"
        elif self.stopped and self.records:
            status = "已停止"
        elif self.records:
            status = "进行中"
        else:
            status = "未开始"
        last_text = ""
        if last:
            mark = {True: "正确", False: "失败"}.get(last["correct"], "未知")
            last_text = f"第{last['question_num']}题 {mark} {last['elapsed_s']:.1f}s"
        return {
            "correct": correct_count,
            "failed": failed_count,
            "accuracy": accuracy,
            "min_seconds": min(times) if times else None,
            "max_seconds": max(times) if times else None,
            "avg_seconds": (sum(times) / len(times)) if times else None,
            "score": self.score,
            "status": status,
            "last_text": last_text,
        }

class QuizSession:
    def __init__(self):
        self.question_id = None
        self.answers = None
        self.question_num = 0
        self.question = None
        self.stopped = False
        self.on_stats = None
        self.stats = AnswerStats()
        # 从配置中获取当前选择的模型
        self.current_model = model_choice

    def start(self):
        """开始答题会话"""
        self.stats = AnswerStats()
        self._load_score()
        self._notify_stats()
        try:
            while self.question_num < 100 and not self.stopped:
                if not self.get_question():
                    logger.error("获取题目失败")
                    return
                
                # 检查是否停止
                if self.stopped:
                    logger.info("答题已停止")
                    return
                
                # 显示题目信息
                self.display_question()
                # 检查是否停止
                if self.stopped:
                    logger.info("答题已停止")
                    return

                started = perf_counter()
                modes = {"4": "DeepSeek + JEV", "3": "自定义模型"}
                logger.info(f"模式: {modes.get(self.current_model, '纯 DeepSeek')}")
                answer = None
                for attempt in range(1, 4):
                    if self.stopped:
                        logger.info("答题已停止")
                        return
                    try:
                        answer = self._model_answer()
                        break
                    except Exception as e:
                        if attempt >= 3:
                            logger.error(f"答题过程发生错误: {e}")
                            return
                        logger.warning(f"答题失败，正在重试（{attempt}/2）: {e}")
                        sleep(1)
                logger.info('AI给出的答案:{}'.format(answer))
                
                # 检查是否停止
                if self.stopped:
                    logger.info("答题已停止")
                    return
                
                try:
                    answer = int(str(answer).strip())
                    if not (1 <= answer <= len(self.answers)):
                        logger.warning(f"无效的答案序号: {answer}")
                        continue
                except ValueError:
                    logger.warning("AI回复其他内容,正在重试")
                    continue

                result = self.answers[answer-1]
                
                # 检查是否停止
                if self.stopped:
                    logger.info("答题已停止")
                    return
                
                submitted, payload = self.submit_answer(result)
                if not submitted:
                    logger.error("提交答案失败")
                    return
                elapsed = perf_counter() - started
                correct = self._record_result(elapsed, payload)
                mark = {True: "正确", False: "失败"}.get(correct, "未知")
                summary = self.stats.snapshot()
                accuracy = "—" if summary["accuracy"] is None else f"{summary['accuracy'] * 100:.0f}%"
                average = "—" if summary["avg_seconds"] is None else f"{summary['avg_seconds']:.1f}s"
                logger.info(
                    f"第{self.question_num}题 {mark} 耗时 {elapsed:.1f}s 平均耗时 {average} "
                    f"得分 {summary['score']} 正确率 {accuracy}"
                )
                if payload.get("finished") or self.question_num >= 100:
                    self.stats.finished = True
                    self._notify_stats()
                    break
        except KeyboardInterrupt:
            logger.info("答题会话已终止")
        except Exception as e:
            logger.error(f"答题过程发生错误: {str(e)}")
        finally:
            if self.stopped and not self.stats.finished:
                self.stats.stopped = True
            self._notify_stats()
    
    def _model_answer(self):
        if self.current_model == '4':
            return decide(self.question, self.answers)
        if self.current_model == '3':
            return CustomAPI().ask(self.get_question_prompt())
        return DeepSeekAPI().ask(self.get_question_prompt())

    # 允许外部更新当前使用的模型
    def update_model_choice(self, new_model_choice):
        """更新当前使用的模型
        
        Args:
            new_model_choice (str): '1' 纯 DeepSeek，'4' DeepSeek + JEV，'3' 自定义模型
        """
        self.current_model = new_model_choice
        logger.info(f"已更新模型选择为: {self.current_model}")

    def get_question(self):
        """获取题目
        
        Returns:
            bool: 是否成功获取题目
        """
        try:
            question = question_get()
            if not question:
                return False

            if question.get('code') != 0:
                logger.info("需要验证码验证")
                return self.handle_verification()

            data = question.get('data', {})
            self.question = data.get('question')
            self.answers = data.get('answers', [])
            self.question_id = data.get('id')
            self.question_num = data.get('question_num', 0)
            return True

        except Exception as e:
            logger.error(f"获取题目失败: {str(e)}")
            return False

    def handle_verification(self):
        """处理验证码验证
        
        Returns:
            bool: 验证是否成功
        """
        try:
            # 检查是否停止
            if self.stopped:
                logger.info("答题已停止")
                return False
                
            logger.info("获取分类信息...")
            category = category_get()
            if not category:
                return False
            
            # 检查是否停止
            if self.stopped:
                logger.info("答题已停止")
                return False
                
            logger.info("分类信息:")
            for cat in category.get('categories', []):
                logger.info(f"ID: {cat.get('id')} - {cat.get('name')}")
            logger.info("tips: 输入多个分类ID请用 *英文逗号* 隔开,例如:1,2,3")
            ids = input('请输入分类ID: ')
            
            # 检查是否停止
            if self.stopped:
                logger.info("答题已停止")
                return False
                
            logger.info("获取验证码...")
            captcha_res = captcha_get()
            logger.info("请打开链接查看验证码内容:{}".format(captcha_res.get('url')))
            if not captcha_res:
                return False
                
            # 检查是否停止
            if self.stopped:
                logger.info("答题已停止")
                return False
                
            captcha = input('请输入验证码: ')

            if captcha_submit(code=captcha, captcha_token=captcha_res.get('token'), ids=ids):
                logger.info("验证通过✅")
                return self.get_question()
            else:
                logger.error("验证失败")
                return False

        except Exception as e:
            logger.error(f"验证过程发生错误: {str(e)}")
            return False

    def display_question(self):
        """显示当前题目和选项"""
        if not self.answers:
            logger.warning("没有可用的题目")
            return

        logger.info(f"第{self.question_num}题:{self.question}")
        for i, answer in enumerate(self.answers, 1):
            logger.info(f"{i}. {answer.get('ans_text')}")
    
    def get_question_prompt(self):
        return '''
        题目:{}
        答案:{}
        '''.format(self.question, self.answers)

    def submit_answer(self, answer):
        """提交答案
        
        Args:
            answer (dict): 答案信息
        
        Returns:
            bool: 是否成功提交答案
        """
        try:
            result = question_submit(
                self.question_id,
                answer.get('ans_hash'),
                answer.get('ans_text')
            )
            if result and result.get('code') == 0:
                logger.info("答案提交成功")
                sleep(1)
                data = result.get('data') if isinstance(result.get('data'), dict) else {}
                return True, data
            if result and result.get('code') == 41105:
                logger.info("答题完成")
                return True, {"finished": True}
            logger.error(f"答案提交失败: {result}")
            return False, {}
        except Exception as e:
            logger.error(f"提交答案时发生错误: {str(e)}")
            return False, {}

    def _load_score(self):
        data = self._read_result()
        score = data.get("score") if data else None
        if isinstance(score, int):
            self.stats.score = score
            self.stats.score_known = True

    def _read_result(self):
        try:
            result = question_result()
        except Exception as e:
            logger.warning(f"读取得分失败: {e}")
            return None
        if not result or result.get("code") != 0:
            return None
        data = result.get("data")
        return data if isinstance(data, dict) else None

    def _record_result(self, elapsed, payload):
        before = self.stats.score
        known = self.stats.score_known
        data = self._read_result()
        score = data.get("score") if data else None
        correct = None
        if isinstance(score, int):
            if known:
                correct = score > before
            self.stats.score = score
            self.stats.score_known = True
        if payload.get("finished"):
            self.stats.finished = True
        self.stats.add(self.question_num, elapsed, correct)
        self._notify_stats()
        return correct

    def _notify_stats(self):
        if self.on_stats:
            self.on_stats(self.stats.snapshot())

# 创建答题会话实例
quiz_session = QuizSession()

def start():
    """启动答题程序"""
    quiz_session.start()
    logger.info('答题结束')