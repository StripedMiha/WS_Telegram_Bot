# WS_Telegram_Bot

технологии: python, asyncio, postgresql, sqlalchemy, alembic, unittest, git, docker
____
### Telegram-bot помощник

Данный бот является самостоятельным тасктрекером для внесения сотрудниками занятности за день в корпоративный тасктрекер. 
Изначально бот был создан как интерфейс для облегчения доступа к стороннему тасктрекеру. Доступ осуществлялся по API.


Доступ к функционалу бота сотрудники могут получить, отправив ему команду `/start`.
Администратору бота придёт сообщение с кнопками выбора: дать доступ или заблокировать пользователя.

По команде `/menu` пользователь вызывает меню взаимодействия с ботом.

![Пример меню](https://cdn.discordapp.com/attachments/712380908388483133/935585157082140672/unknown.png "меню")

Есть несколько способов найти нужную задачу для того, чтобы по шаблону описать чем занимался пользователь.
После отправки пользователем сообщения с текстом трудоёмкости бот дробит внесённые часы по 2 часа (корпоративное требование), 
отправляет по API. В случае успешного отзыва заносит эти трудоёмкости в свою базу данных и уведомляет пользователя об успехе внесения.

Своя база данных нужна для некоей геймификации и мотивации заносить трудоёмкости через бота. 
По командам `/month` и `/week` пользователи могут получить гистограммы за месяц и за неделю соответственно - кто больше всех заносил именно через бота.    
Примеры графиков:    
![Пример гистограммы за месяц](https://cdn.discordapp.com/attachments/712380908388483133/935587819479506954/unknown.png "month")
![Пример гистограммы за неделю](https://cdn.discordapp.com/attachments/712380908388483133/935588238180098178/unknown.png "week")

Раз в день бот рассылает напоминание внести трудоёмкости, если они ещё не внесены.
Раз в неделю бот рассылает круговую диаграмму распределения трудоёмкостей по проектам за неделю.

Пользователи могут:
- Оформить трудоёмкости за день используя интерфейс Telegram.
- Добавить найденную задачу в закладки для более быстрого дальнейшего внесения трудоёмкостей (и удалить закладку).
- Просмотреть отчёт по внесённым, независимо от того как они были внесены - через бота или интерфейс тасктрекера, за сегодня или выбранную дату трудоёмкостям.
- Изменить дату за которую осуществляется внесение трудоёмкостей.
- Изменить время отправки ежедневных напоминаний или отключить их вовсе.
- Отправить админу (через функционал `/menu`) предложение по доработке бота или описать проблему в работе бота.
- Удалить уже внесённые трудоёмкости, независимо от того как они были внесены - через бота или интерфейс тасктрекера.

Администратор бота может:
- Изменить статус пользователя на user/black, используя команду `/change_status`.
- Разослать всем сообщение с новостью или предосторожностью о работе бота, используя команду `/news`.
- Используя команду `/log <имя_лога> <количество_последних_сообщений>`, посмотреть конкретный файл лога или сгруппированный файл лога по типу лога (back, bot).


### Дальнейшие планы:
- [x] Завершить преобразование базы данных, чтобы исключить зависимость от стороннего тасктрекера.
- [x] Добавить функционал для полноценного функционирования как самостоятельный тасктрекер. Например: Создание проектов, создание задач, назначение сотрудников на проект, введение новой роли - менеджер проекта, который создаёт проекты и назначает на них сотрудников.
- [ ] Добавить веб интерфейс.
