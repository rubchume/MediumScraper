from collections.abc import Iterable
import logging
import multiprocessing
import queue
import threading
from typing import Callable, List, Optional, Union

logger = logging.getLogger(f"general_logger.{__name__}")


class MapReduce(object):
    queue_timeout_seconds = 5

    def __init__(
            self,
            function: Callable,
            num_workers: int,
            input_queue: Optional[multiprocessing.Queue] = None,
            output_queue: Optional[multiprocessing.Queue] = None,
            external_workers_to_wait_for=None,
            num_active_workers=None,
            name: Optional[str] = None,
            concurrent=False
    ):
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.name = name

        with num_active_workers.get_lock():
            num_active_workers.value = num_workers

        if not concurrent:
            self.workers: List[Union[threading.Thread, multiprocessing.Process]] = [
                threading.Thread(
                    target=self.run_function_in_loop,
                    daemon=True,
                    args=(
                        function,
                        input_queue,
                        output_queue,
                        external_workers_to_wait_for,
                        num_active_workers,
                        f"{name} (worker {i})"
                    )
                )
                for i in range(num_workers)
            ]
        else:
            self.workers = [
                multiprocessing.Process(
                    target=self.run_function_in_loop,
                    args=(
                        function,
                        input_queue,
                        output_queue,
                        external_workers_to_wait_for,
                        num_active_workers,
                        f"{name} (worker {i})"
                    )
                )
                for i in range(num_workers)
            ]

    def start(self):
        for work in self.workers:
            work.start()

    def join(self):
        for work in self.workers:
            work.join()

    @classmethod
    def run_function_in_loop(
            cls, function, input_queue, output_queue, external_workers_to_wait_for, num_active_workers, name
    ):
        if input_queue is None and output_queue is not None:
            cls._fill_output_queue_until_finished_or_stop_event_is_set(
                function, output_queue, external_workers_to_wait_for, name
            )
        elif input_queue is not None and output_queue is None:
            cls._consume_input_queue_until_stop_event_is_set(
                function, input_queue, external_workers_to_wait_for, name
            )
            cls._consume_input_queue_until_it_is_empty(function, input_queue, name)
        else:
            cls._run_until_stop_event_is_set(function, input_queue, output_queue, external_workers_to_wait_for, name)
            cls._run_until_input_queue_is_empty(function, input_queue, output_queue, name)

        with num_active_workers.get_lock():
            num_active_workers.value -= 1

    @classmethod
    def _put_in_queue(cls, value, q, timeout=5, name="Job name"):
        if isinstance(value, Iterable):
            for element in value:
                cls._put_element_in_queue(element, q, timeout, name)
        else:
            cls._put_element_in_queue(value, q, timeout, name)

    @staticmethod
    def _put_element_in_queue(element, q, timeout=5, name="Job name"):
        while True:
            try:
                q.put(element, block=True, timeout=timeout)
                return
            except queue.Full:
                logger.info(f"{name}. Output queue is full. Trying to put element: {element}")

    @classmethod
    def _fill_output_queue_until_finished_or_stop_event_is_set(
            cls, function, output_queue, external_workers_to_wait_for, name
    ):
        while external_workers_to_wait_for.value > 0:
            try:
                output, is_finished = function()
            except Exception as e:
                logger.info(f"{name}. Error applying function: {e}")
                continue

            cls._put_in_queue(output, output_queue, cls.queue_timeout_seconds, name)

            if is_finished:
                break

    @classmethod
    def _consume_input_queue_until_stop_event_is_set(
            cls, function, input_queue, external_workers_to_wait_for, name
    ):
        while external_workers_to_wait_for.value > 0:
            try:
                input = input_queue.get(block=True, timeout=cls.queue_timeout_seconds)
            except queue.Empty:
                logger.info(f"{name}. Input queue is empty")
                continue

            try:
                function(input)
            except Exception as e:
                logger.info(f"{name}. Error applying function: {e}")
                continue

    @classmethod
    def _consume_input_queue_until_it_is_empty(cls, function, input_queue, name):
        while True:
            try:
                input = input_queue.get_nowait()
            except queue.Empty:
                return

            try:
                function(input)
            except Exception as e:
                logger.info(f"{name}. Error applying function: {e}")
                continue

    @classmethod
    def _run_until_stop_event_is_set(cls, function, input_queue, output_queue, external_workers_to_wait_for, name):
        while external_workers_to_wait_for.value > 0:
            try:
                input = input_queue.get(block=True, timeout=cls.queue_timeout_seconds)
            except queue.Empty:
                logger.info(f"{name}. Input queue is empty")
                continue

            try:
                output = function(input)
            except Exception as e:
                logger.info(f"{name}. Error applying function: {e}")
                continue

            cls._put_element_in_queue(output, output_queue, cls.queue_timeout_seconds, name)

    @classmethod
    def _run_until_input_queue_is_empty(cls, function, input_queue, output_queue, name):
        while True:
            try:
                input = input_queue.get_nowait()
            except queue.Empty:
                return

            try:
                output = function(input)
            except Exception as e:
                logger.info(f"{name}. Error applying function: {e}")
                continue

            cls._put_element_in_queue(output, output_queue, cls.queue_timeout_seconds, name)
