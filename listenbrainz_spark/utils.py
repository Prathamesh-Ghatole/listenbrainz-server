import os
import sys
import errno
import logging
import traceback
from py4j.protocol import Py4JJavaError

import listenbrainz_spark
from listenbrainz_spark import config
from listenbrainz_spark.stats import run_query

from pyspark.sql.utils import AnalysisException

def create_path(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

def register_dataframe(df, table_name):
    """ Creates a view to be used for Spark SQL, etc. Replaces the view if a view with the
        same name exists.

        Args:
            df (dataframe): Dataframe to register.
            table_name (str): Name of the view.
    """
    try:
        df.createOrReplaceTempView(table_name)
    except Py4JJavaError as err:
        raise Py4JJavaError('Cannot register dataframe "{}": {}\n'.format(table_name, type(err).__name__),
            err.java_exception)

def read_files_from_HDFS(path):
    """ Loads the dataframe stored at the given path in HDFS.

        Args:
            path (str): An HDFS path.
    """
    try:
        df = listenbrainz_spark.sql_context.read.parquet(path)
        return df
    except AnalysisException as err:
      raise AnalysisException('Cannot read "{}" from HDFS: {}\n'.format(path, type(err).__name__),
            stackTrace=traceback.format_exc())
    except Py4JJavaError as err:
        raise Py4JJavaError('An error occurred while fetching "{}": {}\n'.format(path, type(err).__name__),
            err.java_exception)

def get_listens(y, m1, m2):
    """ Loads all the listens listened to in a given time window from HDFS.

        Args:
            y (int): Year to load parquets.
            m1 (int): Load parquets from month m1.
            m2 (int): Load parquets till month m2.

        Returns:
            df (dataframe): Dataframe with columns as:
                [
                    'artist_mbids', 'artist_msid', 'artist_name', 'listened_at', 'recording_mbid'
                    'recording_msid', 'release_mbid', 'release_msid', 'release_name', 'tags',
                    'track_name', 'user_name'
                ]
    """
    df = None
    for m in range(m1, m2):
        month = read_files_from_HDFS('{}/data/listenbrainz/{}/{}.parquet'.format(config.HDFS_CLUSTER_URI, y, m))
        df = df.union(month) if df else month
    return df

def save_parquet(df, path):
    """ Save dataframe as parquet to given path in HDFS.

        Args:
            df (dataframe): Dataframe to save.
            path (str): Path in HDFS to save the dataframe.
    """
    try:
        df.write.format('parquet').save(path, mode='overwrite')
    except Py4JJavaError as err:
        raise Py4JJavaError('Cannot save parquet to {}: {}\n'.format(path, type(err).__name__), err.java_exception)
