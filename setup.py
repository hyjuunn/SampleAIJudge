from setuptools import setup, find_packages

setup(
    name="oracle-mvp-ai",  # 패키지명
    version="0.1.26",
    description="AI 판정 시스템 (AiJudge) - 사내 배포용",
    author="el",
    author_email="el2@alocados.io",
    install_requires=[
        "openai==1.93.0",
        "pyyaml==6.0.2",
        "numpy==2.3.1",
        "aiohttp==3.12.13"
    ],
    packages=find_packages(where="lib"),
    package_dir={"": "lib"},
    zip_safe=False,
    include_package_data=True,
)
