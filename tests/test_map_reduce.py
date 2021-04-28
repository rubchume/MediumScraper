import multiprocessing
import queue
import threading
import time
import unittest
from unittest import mock

from src.map_reduce import MapReduce


class MapReduceTests(unittest.TestCase):
    def test_execute_one_worker_for_source_job_with_scalar_output_value(self):
        # Given
        i = [0]

        def function():
            i[0] += 1

            if i[0] >= 5:
                is_finished = True
            else:
                is_finished = False

            return i[0], is_finished

        output_queue = queue.Queue()
        num_active_workers = multiprocessing.Value("i", 0)
        # When
        job = MapReduce(
            function=function,
            num_workers=1,
            output_queue=output_queue,
            external_workers_to_wait_for=multiprocessing.Value("i", 1),
            num_active_workers=num_active_workers,
            name="Job name"
        )
        job.start()
        job.join()
        # Then
        self.assertEqual([1, 2, 3, 4, 5], list(output_queue.queue))
        self.assertEqual(0, num_active_workers.value)
        self.assertEqual(i[0], 5)

    def test_execute_one_worker_for_source_job_with_list_output_value(self):
        # Given
        i = [0]

        def function():
            i[0] += 1

            if i[0] >= 5:
                is_finished = True
            else:
                is_finished = False

            return [i[0], i[0] + 5], is_finished

        output_queue = queue.Queue()
        num_active_workers = multiprocessing.Value("i", 0)
        # When
        job = MapReduce(
            function=function,
            num_workers=1,
            output_queue=output_queue,
            external_workers_to_wait_for=multiprocessing.Value("i", 1),
            num_active_workers=num_active_workers,
            name="Job name"
        )
        job.start()
        job.join()
        # Then
        self.assertEqual([1, 6, 2, 7, 3, 8, 4, 9, 5, 10], list(output_queue.queue))
        self.assertEqual(0, num_active_workers.value)
        self.assertEqual(5, i[0])

    def test_execute_one_worker_for_job_with_scalar_output_value(self):
        # Given
        def function(value):
            return value + 10

        input_queue = queue.Queue()
        for i in [1, 2, 3, 4, 5]:
            input_queue.put(i)

        output_queue = queue.Queue()
        num_active_workers = multiprocessing.Value("i", 0)
        # When
        job = MapReduce(
            function=function,
            num_workers=1,
            input_queue=input_queue,
            output_queue=output_queue,
            external_workers_to_wait_for=multiprocessing.Value("i", 0),
            num_active_workers=num_active_workers,
            name="Job name"
        )
        job.start()
        job.join()

        # Then
        self.assertEqual([11, 12, 13, 14, 15], list(output_queue.queue))
        self.assertEqual(0, num_active_workers.value)

    def test_execute_one_worker_for_job_with_list_output_value(self):
        # Given
        def function(value):
            return value, value + 10

        input_queue = queue.Queue()
        for i in [1, 2, 3, 4, 5]:
            input_queue.put(i)

        output_queue = queue.Queue()
        num_active_workers = multiprocessing.Value("i", 0)
        # When
        job = MapReduce(
            function=function,
            num_workers=1,
            input_queue=input_queue,
            output_queue=output_queue,
            external_workers_to_wait_for=multiprocessing.Value("i", 0),
            num_active_workers=num_active_workers,
            name="Job name"
        )
        job.start()
        job.join()

        # Then
        self.assertEqual([(1, 11), (2, 12), (3, 13), (4, 14), (5, 15)], list(output_queue.queue))
        self.assertEqual(0, num_active_workers.value)

    def test_execute_one_worker_for_sink_job(self):
        # Given
        inputs = []

        def function(value):
            inputs.append(value)

        input_queue = queue.Queue()
        for i in [1, 2, 3, 4, 5]:
            input_queue.put(i)

        num_active_workers = multiprocessing.Value("i", 0)
        # When
        job = MapReduce(
            function=function,
            num_workers=1,
            input_queue=input_queue,
            external_workers_to_wait_for=multiprocessing.Value("i", 0),
            num_active_workers=num_active_workers,
            name="Job name"
        )
        job.start()
        job.join()

        # Then
        self.assertEqual([1, 2, 3, 4, 5], inputs)
        self.assertEqual(0, num_active_workers.value)

    def test_execute_one_worker_for_sink_job_is_tolerant_to_errors(self):
        # Given
        inputs = []

        def function(value):
            if value == 3:
                raise RuntimeError("error message")
            inputs.append(value)

        input_queue = queue.Queue()
        for i in [1, 2, 3, 4, 5]:
            input_queue.put(i)

        num_active_workers = multiprocessing.Value("i", 0)
        # When
        job = MapReduce(
            function=function,
            num_workers=1,
            input_queue=input_queue,
            external_workers_to_wait_for=multiprocessing.Value("i", 0),
            num_active_workers=num_active_workers,
            name="Job name"
        )
        job.start()
        job.join()

        # Then
        self.assertEqual([1, 2, 4, 5], inputs)
        self.assertEqual(0, num_active_workers.value)

    def test_execute_one_worker_for_sink_job_with_external_stop(self):
        # Given
        inputs = []

        def function(value):
            inputs.append(value)

        input_queue = queue.Queue()
        for i in [1, 2, 3, 4, 5]:
            input_queue.put(i)

        num_active_workers = multiprocessing.Value("i", 0)
        external_workers_to_wait_for = multiprocessing.Value("i", 1)
        # When
        job = MapReduce(
            function=function,
            num_workers=1,
            input_queue=input_queue,
            external_workers_to_wait_for=external_workers_to_wait_for,
            num_active_workers=num_active_workers,
            name="Job name"
        )
        job.start()
        time.sleep(0.5)
        with external_workers_to_wait_for.get_lock():
            external_workers_to_wait_for.value = 0
        job.join()

        # Then
        self.assertEqual([1, 2, 3, 4, 5], inputs)
        self.assertEqual(0, num_active_workers.value)

    def test_execute_one_worker_for_sink_job_with_external_stop_is_tolerant_to_errors(self):
        # Given
        inputs = []

        def function(value):
            if value == 3:
                raise RuntimeError("error message")
            inputs.append(value)

        input_queue = queue.Queue()
        for i in [1, 2, 3, 4, 5]:
            input_queue.put(i)

        num_active_workers = multiprocessing.Value("i", 0)
        external_workers_to_wait_for = multiprocessing.Value("i", 1)
        # When
        job = MapReduce(
            function=function,
            num_workers=1,
            input_queue=input_queue,
            external_workers_to_wait_for=external_workers_to_wait_for,
            num_active_workers=num_active_workers,
            name="Job name"
        )
        job.start()
        time.sleep(0.5)
        with external_workers_to_wait_for.get_lock():
            external_workers_to_wait_for.value = 0
        job.join()

        # Then
        self.assertEqual([1, 2, 4, 5], inputs)
        self.assertEqual(0, num_active_workers.value)

    def test_execute_many_workers_for_job(self):
        def function(value):
            if value == 1:
                time.sleep(1)

            return value + 10

        input_queue = queue.Queue()
        for i in range(1, 11):
            input_queue.put(i)

        output_queue = queue.Queue()
        num_active_workers = multiprocessing.Value("i", 0)
        # When
        job = MapReduce(
            function=function,
            num_workers=10,
            input_queue=input_queue,
            output_queue=output_queue,
            external_workers_to_wait_for=multiprocessing.Value("i", 0),
            num_active_workers=num_active_workers,
            name="Job name"
        )
        job.start()
        job.join()
        # Then
        self.assertEqual(list(range(12, 21)) + [11], list(output_queue.queue))
        self.assertEqual(0, num_active_workers.value)

    def test_set_finished_event_only_when_all_workers_have_finished(self):
        def function(value):
            if value == 1:
                time.sleep(1)

            return time.time()

        finished_time = [0]

        def register_when_finished_is_set():
            while True:
                if num_active_workers.value == 0:
                    finished_time[0] = time.time()
                    return

        input_queue = queue.Queue()
        for i in range(1, 11):
            input_queue.put(i)

        output_queue = queue.Queue()
        num_active_workers = multiprocessing.Value("i", 0)
        # When
        job = MapReduce(
            function=function,
            num_workers=10,
            input_queue=input_queue,
            output_queue=output_queue,
            external_workers_to_wait_for=multiprocessing.Value("i", 0),
            num_active_workers=num_active_workers,
            name="Job name"
        )
        job.start()

        aux = threading.Thread(
            target=register_when_finished_is_set,
            daemon=True,
            args=(),
        )
        aux.start()

        job.join()
        aux.join()

        # Then
        self.assertEqual(0, num_active_workers.value)
        last_time = max(list(output_queue.queue))
        self.assertTrue(last_time <= finished_time[0])

    def test_execute_many_workers_for_job_concurrently(self):
        input_queue = multiprocessing.Queue()
        for i in range(1, 11):
            input_queue.put(i)

        output_queue = multiprocessing.Queue()
        num_active_workers = multiprocessing.Value("i", 0)
        # When
        job = MapReduce(
            function=self.function,
            num_workers=10,
            input_queue=input_queue,
            output_queue=output_queue,
            external_workers_to_wait_for=multiprocessing.Value("i", 0),
            num_active_workers=num_active_workers,
            name="Job name",
            concurrent=True
        )
        job.start()
        job.join()

        # Then
        self.assertEqual(list(range(11, 21)), self.queue_to_list(output_queue))
        self.assertEqual(0, num_active_workers.value)

    def test_do_not_hang_when_external_workers_to_wait_for_becomes_0(self):
        input_queue = multiprocessing.Queue()

        output_queue = multiprocessing.Queue()
        external_workers_to_wait_for = multiprocessing.Value("i", 1)
        num_active_workers = multiprocessing.Value("i", 0)
        # When
        job = MapReduce(
            function=self.function,
            num_workers=2,
            input_queue=input_queue,
            output_queue=output_queue,
            external_workers_to_wait_for=external_workers_to_wait_for,
            num_active_workers=num_active_workers,
            name="Job name",
            concurrent=True
        )
        job.start()
        time.sleep(1)
        with external_workers_to_wait_for.get_lock():
            external_workers_to_wait_for.value = 0
        job.join()

        # Then
        self.assertEqual([], self.queue_to_list(output_queue))
        self.assertEqual(0, num_active_workers.value)

    @classmethod
    def function(cls, value):
        time.sleep(value)

        return value + 10

    @classmethod
    def queue_to_list(cls, queue: multiprocessing.Queue):
        x = []
        while not queue.empty():
            x.append(queue.get_nowait())

        return x

    def test_execute_one_worker_for_source_job_is_tolerant_to_errors(self):
        # Given
        i = [0]

        def function():
            i[0] += 1

            if i[0] >= 5:
                is_finished = True
            elif i[0] == 3:
                raise RuntimeError("Error message")
            else:
                is_finished = False

            return i[0], is_finished

        output_queue = queue.Queue()
        num_active_workers = multiprocessing.Value("i", 0)
        # When
        job = MapReduce(
            function=function,
            num_workers=1,
            output_queue=output_queue,
            external_workers_to_wait_for=multiprocessing.Value("i", 1),
            num_active_workers=num_active_workers,
            name="Job name"
        )
        job.start()
        job.join()
        # Then
        self.assertEqual([1, 2, 4, 5], list(output_queue.queue))
        self.assertEqual(0, num_active_workers.value)
        self.assertEqual(i[0], 5)

    def test_execute_one_worker_for_source_job_with_external_stop_is_tolerant_to_errors(self):
        # Given
        i = [0]

        def function():
            i[0] += 1

            if i[0] % 5:
                raise RuntimeError("error message")

            return 0, False

        output_queue = queue.Queue()
        num_active_workers = multiprocessing.Value("i", 1)
        external_workers_to_wait_for = multiprocessing.Value("i", 1)
        # When
        job = MapReduce(
            function=function,
            num_workers=1,
            output_queue=output_queue,
            external_workers_to_wait_for=external_workers_to_wait_for,
            num_active_workers=num_active_workers,
            name="Job name"
        )
        job.start()
        time.sleep(0.5)
        with external_workers_to_wait_for.get_lock():
            external_workers_to_wait_for.value = 0
        job.join()
        # Then
        self.assertEqual(1, len(set(list(output_queue.queue))))
        self.assertEqual(0, num_active_workers.value)

    @mock.patch("src.map_reduce.logger.info")
    def test_put_element_in_queue_is_tolerant_to_delays(self, logger_info_mock):
        # Given
        q = multiprocessing.Queue(maxsize=1)
        q.put(1)
        # When
        t = threading.Thread(
            target=MapReduce._put_element_in_queue,
            daemon=True,
            args=(2, q, 1, "Job name"),
        )
        t.start()
        time.sleep(2)
        q.get()
        t.join()
        # Then
        self.assertEqual(2, q.get())
        logger_info_mock.assert_called_with("Job name. Output queue is full. Trying to put element: 2")

    def test_execute_one_worker_for_source_job_stop_externally(self):
        # Given
        def function():
            return 0, False

        output_queue = queue.Queue()
        num_active_workers = multiprocessing.Value("i", 1)
        external_workers_to_wait_for = multiprocessing.Value("i", 1)
        # When
        job = MapReduce(
            function=function,
            num_workers=1,
            output_queue=output_queue,
            external_workers_to_wait_for=external_workers_to_wait_for,
            num_active_workers=num_active_workers,
            name="Job name"
        )
        job.start()
        time.sleep(0.5)
        with external_workers_to_wait_for.get_lock():
            external_workers_to_wait_for.value = 0
        job.join()
        # Then
        self.assertEqual(1, len(set(list(output_queue.queue))))
        self.assertEqual(0, num_active_workers.value)

    def test_execute_one_worker_for_job_is_tolerant_to_errors(self):
        # Given
        def function(value):
            if value == 3:
                raise RuntimeError("some error")
            return value + 10

        input_queue = queue.Queue()
        for i in [1, 2, 3, 4, 5]:
            input_queue.put(i)

        output_queue = queue.Queue()
        num_active_workers = multiprocessing.Value("i", 0)
        # When
        job = MapReduce(
            function=function,
            num_workers=1,
            input_queue=input_queue,
            output_queue=output_queue,
            external_workers_to_wait_for=multiprocessing.Value("i", 0),
            num_active_workers=num_active_workers,
            name="Job name"
        )
        job.start()
        job.join()

        # Then
        self.assertEqual([11, 12, 14, 15], list(output_queue.queue))
        self.assertEqual(0, num_active_workers.value)

    def test_execute_one_worker_for_job_stop_externally(self):
        # Given
        def function(value):
            return value + 10

        input_queue = queue.Queue()
        for i in [1, 2, 3, 4, 5]:
            input_queue.put(i)

        output_queue = queue.Queue()
        num_active_workers = multiprocessing.Value("i", 0)
        external_workers_to_wait_for = multiprocessing.Value("i", 1)
        # When
        job = MapReduce(
            function=function,
            num_workers=1,
            input_queue=input_queue,
            output_queue=output_queue,
            external_workers_to_wait_for=external_workers_to_wait_for,
            num_active_workers=num_active_workers,
            name="Job name"
        )
        job.start()
        time.sleep(0.5)
        with external_workers_to_wait_for.get_lock():
            external_workers_to_wait_for.value = 0
        job.join()

        # Then
        self.assertEqual([11, 12, 13, 14, 15], list(output_queue.queue))
        self.assertEqual(0, num_active_workers.value)

    def test_execute_one_worker_for_job_stop_externally_is_tolerant_to_errors(self):
        # Given
        def function(value):
            if value == 3:
                raise RuntimeError("error message")

            return value + 10

        input_queue = queue.Queue()
        for i in [1, 2, 3, 4, 5]:
            input_queue.put(i)

        output_queue = queue.Queue()
        num_active_workers = multiprocessing.Value("i", 0)
        external_workers_to_wait_for = multiprocessing.Value("i", 1)
        # When
        job = MapReduce(
            function=function,
            num_workers=1,
            input_queue=input_queue,
            output_queue=output_queue,
            external_workers_to_wait_for=external_workers_to_wait_for,
            num_active_workers=num_active_workers,
            name="Job name"
        )
        job.start()
        time.sleep(0.5)
        with external_workers_to_wait_for.get_lock():
            external_workers_to_wait_for.value = 0
        job.join()

        # Then
        self.assertEqual([11, 12, 14, 15], list(output_queue.queue))
        self.assertEqual(0, num_active_workers.value)
