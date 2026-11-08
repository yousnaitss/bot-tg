import aiosqlite


DATABASE_NAME = "study.db"


# ==========================================
# СОЗДАНИЕ БАЗЫ ДАННЫХ
# ==========================================

async def init_db():
    async with aiosqlite.connect(DATABASE_NAME) as db:

        await db.execute("""
            CREATE TABLE IF NOT EXISTS homework (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                due_date TEXT NOT NULL,
                description TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                note_date TEXT
            )
        """)

        await db.commit()


# ==========================================
# ДОМАШНИЕ ЗАДАНИЯ
# ==========================================

async def add_homework(
    user_id,
    subject,
    due_date,
    description
):
    async with aiosqlite.connect(DATABASE_NAME) as db:

        await db.execute(
            """
            INSERT INTO homework
            (user_id, subject, due_date, description)
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                subject,
                due_date,
                description
            )
        )

        await db.commit()


async def get_homework_by_date(
    user_id,
    due_date
):
    async with aiosqlite.connect(DATABASE_NAME) as db:

        cursor = await db.execute(
            """
            SELECT id, subject, description, completed
            FROM homework
            WHERE user_id = ?
            AND due_date = ?
            ORDER BY id
            """,
            (
                user_id,
                due_date
            )
        )

        return await cursor.fetchall()


async def get_all_homework(user_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:

        cursor = await db.execute(
            """
            SELECT
                id,
                subject,
                due_date,
                description,
                completed
            FROM homework
            WHERE user_id = ?
            ORDER BY due_date, id
            """,
            (user_id,)
        )

        return await cursor.fetchall()


async def get_homework(
    homework_id,
    user_id
):
    async with aiosqlite.connect(DATABASE_NAME) as db:

        cursor = await db.execute(
            """
            SELECT
                id,
                subject,
                due_date,
                description,
                completed
            FROM homework
            WHERE id = ?
            AND user_id = ?
            """,
            (
                homework_id,
                user_id
            )
        )

        return await cursor.fetchone()


async def complete_homework(
    homework_id,
    user_id
):
    async with aiosqlite.connect(DATABASE_NAME) as db:

        await db.execute(
            """
            UPDATE homework
            SET completed = 1
            WHERE id = ?
            AND user_id = ?
            """,
            (
                homework_id,
                user_id
            )
        )

        await db.commit()


async def delete_homework(
    homework_id,
    user_id
):
    async with aiosqlite.connect(DATABASE_NAME) as db:

        await db.execute(
            """
            DELETE FROM homework
            WHERE id = ?
            AND user_id = ?
            """,
            (
                homework_id,
                user_id
            )
        )

        await db.commit()


async def update_homework_subject(
    homework_id,
    user_id,
    subject
):
    async with aiosqlite.connect(DATABASE_NAME) as db:

        await db.execute(
            """
            UPDATE homework
            SET subject = ?
            WHERE id = ?
            AND user_id = ?
            """,
            (
                subject,
                homework_id,
                user_id
            )
        )

        await db.commit()


async def update_homework_date(
    homework_id,
    user_id,
    due_date
):
    async with aiosqlite.connect(DATABASE_NAME) as db:

        await db.execute(
            """
            UPDATE homework
            SET due_date = ?
            WHERE id = ?
            AND user_id = ?
            """,
            (
                due_date,
                homework_id,
                user_id
            )
        )

        await db.commit()


async def update_homework_description(
    homework_id,
    user_id,
    description
):
    async with aiosqlite.connect(DATABASE_NAME) as db:

        await db.execute(
            """
            UPDATE homework
            SET description = ?
            WHERE id = ?
            AND user_id = ?
            """,
            (
                description,
                homework_id,
                user_id
            )
        )

        await db.commit()


# ==========================================
# ЗАМЕТКИ
# ==========================================

async def add_note(
    user_id,
    text,
    note_date=None
):
    async with aiosqlite.connect(DATABASE_NAME) as db:

        await db.execute(
            """
            INSERT INTO notes
            (user_id, text, note_date)
            VALUES (?, ?, ?)
            """,
            (
                user_id,
                text,
                note_date
            )
        )

        await db.commit()


async def get_notes_by_date(
    user_id,
    note_date
):
    async with aiosqlite.connect(DATABASE_NAME) as db:

        cursor = await db.execute(
            """
            SELECT id, text
            FROM notes
            WHERE user_id = ?
            AND note_date = ?
            ORDER BY id
            """,
            (
                user_id,
                note_date
            )
        )

        return await cursor.fetchall()


async def get_all_notes(user_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:

        cursor = await db.execute(
            """
            SELECT id, text, note_date
            FROM notes
            WHERE user_id = ?
            ORDER BY
                CASE
                    WHEN note_date IS NULL THEN 1
                    ELSE 0
                END,
                note_date,
                id
            """,
            (user_id,)
        )

        return await cursor.fetchall()


async def get_note(
    note_id,
    user_id
):
    async with aiosqlite.connect(DATABASE_NAME) as db:

        cursor = await db.execute(
            """
            SELECT id, text, note_date
            FROM notes
            WHERE id = ?
            AND user_id = ?
            """,
            (
                note_id,
                user_id
            )
        )

        return await cursor.fetchone()


async def update_note_text(
    note_id,
    user_id,
    text
):
    async with aiosqlite.connect(DATABASE_NAME) as db:

        await db.execute(
            """
            UPDATE notes
            SET text = ?
            WHERE id = ?
            AND user_id = ?
            """,
            (
                text,
                note_id,
                user_id
            )
        )

        await db.commit()


async def update_note_date(
    note_id,
    user_id,
    note_date
):
    async with aiosqlite.connect(DATABASE_NAME) as db:

        await db.execute(
            """
            UPDATE notes
            SET note_date = ?
            WHERE id = ?
            AND user_id = ?
            """,
            (
                note_date,
                note_id,
                user_id
            )
        )

        await db.commit()


async def delete_note(
    note_id,
    user_id
):
    async with aiosqlite.connect(DATABASE_NAME) as db:

        await db.execute(
            """
            DELETE FROM notes
            WHERE id = ?
            AND user_id = ?
            """,
            (
                note_id,
                user_id
            )
        )

        await db.commit()