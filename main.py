import base64
import getpass
import logging
import random
import re
import sys
import time
import urllib.parse
import warnings
from collections import namedtuple
from datetime import datetime
from typing import Dict, Sequence

import requests
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from bs4 import BeautifulSoup, GuessedAtParserWarning


class RSACrypto:
    def __init__(self, pub_key: str) -> None:
        rsa_key = RSA.import_key(f"-----BEGIN PUBLIC KEY-----\n{pub_key}\n-----END PUBLIC KEY-----")
        self.rsa = PKCS1_v1_5.new(rsa_key)

    def encrypt(self, plain: str) -> str:
        cipher = self.rsa.encrypt(plain.encode("utf-8"))
        return base64.b64encode(cipher).decode("ascii")


CourseInfo = namedtuple("CourseInfo", ["name", "department_id"])


def parse_host(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def main(username: str, password: str, courses: Sequence[str]):
    sess = requests.Session()
    sess.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.50"
    index_url = "https://sep.ucas.ac.cn"
    current_host = index_url
    index_res = sess.get(index_url)
    index_soup = BeautifulSoup(index_res.text)
    key_pattern = re.compile(r"jsePubKey = '([+/\dA-Za-z]+)'")
    encrypt_script = index_soup.find("script", string=key_pattern)
    if encrypt_script is None:
        logging.error("RSA公钥获取失败")
        return
    pub_key = key_pattern.search(encrypt_script.text).group(1)
    logging.info("RSA公钥获取成功：%s", pub_key)
    login_form = index_soup.find("form", attrs={"id": "sepform"})
    login_url = current_host + login_form.get("action")
    login_data = {input_node.get("name"): input_node.get("value") for input_node in login_form.find_all("input", attrs={"name": True})}
    login_data["userName"] = username
    login_data["pwd"] = RSACrypto(pub_key).encrypt(password)
    login_res = sess.post(login_url, data=login_data)
    if "密码错误" in login_res.text:
        logging.error("用户名或密码错误")
        return
    logging.info("登录成功：%s", username)
    store_soup = BeautifulSoup(login_res.text)
    portal_url = current_host + store_soup.find("a", attrs={"title": "选课系统"}).get("href")
    portal_res = sess.get(portal_url)
    portal_soup = BeautifulSoup(portal_res.text)
    redirect_pattern = re.compile(r"window.location.href='(https://[#$%&+,-./0-9:;=?@A-Z_a-z]+)'")
    redirect_script = portal_soup.find("script", string=redirect_pattern)
    if redirect_script is None:
        logging.error("选课系统跳转链接获取失败")
        return
    redirect_url = redirect_pattern.search(redirect_script.text).group(1)
    current_host = parse_host(redirect_url)
    logging.info("选课系统跳转链接获取成功：%s", redirect_url)
    jwxk_res = sess.get(redirect_url)
    jwxk_soup = BeautifulSoup(jwxk_res.text)
    schedule_url = current_host + jwxk_soup.find("a", string="学期课表").get("href")
    schedule_res = sess.get(schedule_url)
    schedule_soup = BeautifulSoup(schedule_res.text)
    department_select = schedule_soup.find("select", attrs={"name": "deptId"})
    department_map = {option_node.text: option_node.get("value") for option_node in department_select.find_all("option")}
    course_map: Dict[str, CourseInfo] = {}
    course_index = 1
    for tr_node in schedule_soup.find_all("tr"):
        td_nodes = tr_node.find_all("td")
        if len(td_nodes) >= 9 and td_nodes[0].text == str(course_index):
            course_map[td_nodes[2].text] = CourseInfo(td_nodes[3].text, department_map[td_nodes[1].text])
            course_index += 1
    if course_index == 1:
        logging.error("课程列表加载失败")
        return
    logging.info("课程列表加载成功，共计%d门课程", course_index - 1)
    manage_url = current_host + jwxk_soup.find("a", string="选择课程").get("href")
    manage_res = sess.get(manage_url)
    manage_soup = BeautifulSoup(manage_res.text)
    select_form = manage_soup.find("form", attrs={"id": "regfrm2"})
    select_url = current_host + select_form.get("action")
    select_data = [("sb", 0)]
    for department_id in set(course_map[course_id].department_id for course_id in courses):
        select_data.append(("deptIds", department_id))
    courses_set = set(courses)
    while True:
        select_res = sess.post(select_url, select_data)
        select_soup = BeautifulSoup(select_res.text)
        available_courses = []
        for tr_node in select_soup.find_all("tr"):
            td_nodes = tr_node.find_all("td")
            if len(td_nodes) == 13 and td_nodes[3].text in courses_set:
                checkbox_node = td_nodes[0].find("input", attrs={"type": "checkbox", "name": "sids"})
                if checkbox_node is not None and checkbox_node.get("disabled") is None:
                    available_courses.append(checkbox_node.get("value") + "_" + td_nodes[4].text)
        logging.info("[%s]可选课程：%s", datetime.now().strftime("%H:%M:%S"), "、".join(available_courses))
        time.sleep(random.randint(120, 180))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    warnings.filterwarnings("ignore", category=GuessedAtParserWarning)
    username = None
    password = None
    courses = None
    for i in range(1, len(sys.argv)):
        if i == 1:
            username = sys.argv[1]
        elif i == 2:
            password = sys.argv[2]
        elif i == 3:
            courses = sys.argv[3:]
            break
    if username is None:
        username = input("用户名：")
    if password is None:
        password = getpass.getpass("密码：")
    if courses is None:
        courses = input("课程编号：").split()
    main(username, password, courses)
