from __future__ import annotations

import argparse
import datetime
import json
import sys

import pandas as pd
import requests
from pydantic import BaseModel, ValidationError
from sqlalchemy import create_engine, text
from sqlalchemy.engine.base import Engine


class Credentials(BaseModel):
    login: str
    password: str

    @classmethod
    def from_file(cls, file_path: str) -> Credentials:
        """
        Parse connection arguments from .json file under 'credentials' key

        Parameters
        ----------
            file_path : str
                Path to the file to parse.

        Returns
        -------
            Credentials
                Instance of the class.
        """
        try:
            with open(file_path) as json_file:
                return cls(**json.load(json_file)["time_tracking_creds"])
        except ValidationError:
            sys.exit("Not appropriate number of parameters or they have incorrect types")


class DB(BaseModel):
    db_name: str
    table_name: str
    user: str
    password: str
    host: str
    port: str

    def get_engine(self) -> Engine:
        """
        Create engine for the database.

        Returns
        -------
            Engine
                SQLAlchemy engine.
        """
        engine = create_engine(
            f'postgresql://'
            f'{self.user}:'
            f'{self.password}@'
            f'{self.host}:'
            f'{self.port}/'
            f'{self.db_name}',
            future=True
        )
        return engine

    @classmethod
    def from_file(cls, file_path: str) -> DB:
        """
        Parse connection arguments from .json file under 'db' key

        Parameters
        ----------
            file_path : str
                Path to the file to parse.

        Returns
        -------
            DB
                Instance of the class.
        """
        try:
            with open(file_path) as json_file:
                return cls(**json.load(json_file)["db"])
        except ValidationError:
            sys.exit("Not appropriate number of parameters or they have incorrect types")


def get_path() -> str:
    """
    Get path to connections file passed as argument.

    Returns
    -------
        str
            Path to the connections file.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--path',
                        type=str,
                        dest='path',
                        help='Path to the connections file')
    args = parser.parse_args()
    path_to_file = args.path
    if not path_to_file:
        path_to_file = "connections.json"
    return path_to_file


def create_table(db: DB) -> None:
    """
    Create table in the specified database

    Parameters
    ----------
        db : DB
            Class, providing connection to the database.

    Returns
    -------
        None
    """
    engine = db.get_engine()
    with engine.connect() as connection:
        table_creation = text(
            '''
            CREATE TABLE IF NOT EXISTS :table_name (
                creation_date date,
                project varchar(64),
                accumulated_time_s int NOT NULL,
                username varchar(64),
                task varchar(128),
                task_time_s int NOT NULL
            );
            '''
        )
        connection.execute(table_creation, {"table_name": db.table_name})
        connection.commit()


def make_tasks_df(credentials: Credentials,
                  url: str = 'https://app.trackingtime.co/api/v4/tasks') -> pd.DataFrame:
    """
    Create dataframe with the necessary fields to describe tasks
    in the TimeTracking web application.

    Parameters
    ----------
        credentials : Credentials
            Class with the login and password fields.

        url : str
            Url to the get tasks endpoint. It may be modified in the future.

    Returns
    -------
        pd.DataFrame
            Dataframe, containing all the tasks from all the projects.
    """

    login = credentials.login
    password = credentials.password
    tasks_data_response = requests.get(url, auth=(login, password))
    tasks_data = tasks_data_response.json()['data']
    tasks_df = pd.DataFrame({"date": [],
                             "project_name": [],
                             "project_time": [],
                             "assignee_name": [],
                             "task_name": [],
                             "task_time": []})
    for task_index in range(len(tasks_data)):
        if tasks_data[task_index]['project'] is None:
            continue
        date = datetime.datetime.now().strftime('%Y-%m-%d')
        project_name = tasks_data[task_index]['project']
        project_time = tasks_data[task_index]['project_accumulated_time']
        assignee_name = tasks_data[task_index]['user']['name']
        task_name = tasks_data[task_index]['name']
        task_time = tasks_data[task_index]['accumulated_time']
        task_df = pd.DataFrame({"date": [date],
                                "project_name": [project_name],
                                "project_time": [project_time],
                                "assignee_name": [assignee_name],
                                "task_name": [task_name],
                                "task_time": [task_time]})
        tasks_df = pd.concat([tasks_df, task_df], axis=0)

    tasks_df = tasks_df.reset_index(drop=True)
    return tasks_df


def insert_to_table(db: DB, tasks_df: pd.DataFrame) -> None:
    """
    Insert tasks information to the SQL table

    Parameters
    ----------
        db : DB
            Class, providing connection to the database.

        tasks_df : pd.DataFrame
            Dataframe, containing all the tasks from all the projects.

    Returns
    -------
        None
    """
    engine = db.get_engine()
    with engine.connect() as connection:
        tasks_df.to_sql(
            name=db.table_name,
            schema='public',
            if_exists='append',
            con=connection,
            index=False
        )
        connection.commit()


def main():
    """Put all the functions together and add tasks info to the SQL table"""
    path_to_file = get_path()
    credentials = Credentials.from_file(path_to_file)
    db = DB.from_file(path_to_file)

    create_table(db)
    tasks_df = make_tasks_df(credentials)
    insert_to_table(db, tasks_df)


if __name__ == '__main__':
    main()
