import unittest

from ikabot.bot.transportGoodsBot import TransportJob, TransportGoodsBot

job_1_2__1 = TransportJob(
    origin_city={'id': 1, 'name': 'City1'},
    target_city={'id': 2, 'name': 'City2'},
    resources=[1, 2, 3, 4, 5]
)
job_1_2__2 = TransportJob(
    origin_city={'id': 1, 'name': 'City1'},
    target_city={'id': 2, 'name': 'City2'},
    resources=[2, 3, 4, 5, 6]
)
job_1_3__1 = TransportJob(
    origin_city={'id': 1, 'name': 'City1'},
    target_city={'id': 3, 'name': 'City3'},
    resources=[7, 8, 9, 10, 11]
)
job_1_2__result = TransportJob(
    origin_city={'id': 1, 'name': 'City1'},
    target_city={'id': 2, 'name': 'City2'},
    resources=[3, 5, 7, 9, 11]
)

class TestOptimizeJobs(unittest.TestCase):

    def test_optimize_jobs_no_jobs(self):
        # Test when there are no jobs
        jobs = []
        result = TransportGoodsBot.optimize_jobs(jobs)
        self.assertEqual(result, [])

    def test_optimize_jobs_single_job(self):
        # Test when there is only one job
        jobs = [job_1_2__1]
        result = TransportGoodsBot.optimize_jobs(jobs)
        self.assertEqual(result, jobs)

    def test_optimize_jobs_multiple_jobs_same_cities(self):
        # Test when there are multiple jobs with the same origin and target cities
        jobs = [job_1_2__1, job_1_2__2]
        result = TransportGoodsBot.optimize_jobs(jobs)
        expected_result = [job_1_2__result]
        self.assertEqual(result, expected_result)

    def test_optimize_jobs_multiple_jobs_different_cities(self):
        # Test when there are multiple jobs with different origin and target cities
        jobs = [job_1_2__1, job_1_3__1]
        result = TransportGoodsBot.optimize_jobs(jobs)
        expected_result = jobs  # Since origin and target cities are different, no optimization should occur
        self.assertEqual(result, expected_result)

    def test_optimize_jobs_merge_and_remain(self):
        # Test when two jobs are merged, and one remains the same
        jobs = [job_1_2__1, job_1_2__2, job_1_3__1]
        result = TransportGoodsBot.optimize_jobs(jobs)
        expected_result = [
            job_1_2__result,
            job_1_3__1  # job_1_3__1 remains the same
        ]
        self.assertEqual(result, expected_result)
