import React, { useEffect, useState } from 'react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || '/api';

function TaskTracker() {
    const [tasks, setTasks] = useState([]);
    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [status, setStatus] = useState('pending');
    const [file, setFile] = useState(null);
    const [editingTask, setEditingTask] = useState(null);

    const fetchTasks = async () => {
        try {
            const response = await axios.get(`${API_URL}/tasks`);
            setTasks(response.data);
        } catch (error) {
            console.error('Ошибка при загрузке задач:', error);
        }
    };

    useEffect(() => {
        fetchTasks();
    }, []);

    const addTask = async () => {
        if (!title) return alert('Введите название задачи');
        try {
            const formData = new FormData();
            formData.append('title', title);
            formData.append('description', description);
            if (file) formData.append('image', file);

            await axios.post(`${API_URL}/tasks`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });

            setTitle('');
            setDescription('');
            setFile(null);
            fetchTasks();
        } catch (error) {
            console.error('Ошибка при создании задачи:', error);
        }
    };

    const deleteTask = async (taskId) => {
        try {
            await axios.delete(`${API_URL}/tasks/${taskId}`);
            fetchTasks();
        } catch (error) {
            console.error('Ошибка при удалении задачи:', error);
        }
    };

    const startEdit = (task) => {
        setEditingTask(task);
        setTitle(task.title);
        setDescription(task.description);
        setStatus(task.status || 'pending');
        setFile(null);
    };

    const cancelEdit = () => {
        setEditingTask(null);
        setTitle('');
        setDescription('');
        setStatus('pending');
        setFile(null);
    };

    const saveTask = async () => {
        if (!title) return alert('Введите название задачи');
        try {
            const formData = new FormData();
            formData.append('title', title);
            formData.append('description', description);
            formData.append('status', status);
            if (file) formData.append('image', file);

            await axios.put(`${API_URL}/tasks/${editingTask.id}`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });

            cancelEdit();
            fetchTasks();
        } catch (error) {
            console.error('Ошибка при обновлении задачи:', error);
        }
    };

    // Стили
    const styles = {
        container: { padding: '20px', fontFamily: 'Arial, sans-serif', maxWidth: '800px', margin: '0 auto' },
        header: { textAlign: 'center', marginBottom: '30px', color: '#333' },
        form: { display: 'flex', flexWrap: 'wrap', gap: '10px', marginBottom: '20px', alignItems: 'center' },
        input: { padding: '8px', borderRadius: '5px', border: '1px solid #ccc', flex: '1' },
        select: { padding: '8px', borderRadius: '5px', border: '1px solid #ccc' },
        button: { padding: '8px 15px', borderRadius: '5px', border: 'none', cursor: 'pointer', backgroundColor: '#4CAF50', color: '#fff' },
        cancelButton: { backgroundColor: '#f44336', color: '#fff' },
        taskList: { listStyle: 'none', padding: 0 },
        taskItem: { padding: '15px', marginBottom: '15px', borderRadius: '8px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)', backgroundColor: '#fff' },
        taskImage: { maxWidth: '200px', marginTop: '10px', borderRadius: '5px' },
        taskButtons: { marginTop: '10px', display: 'flex', gap: '10px' }
    };

    return (
        <div style={styles.container}>
            <h1 style={styles.header}>Task Tracker</h1>

            <div style={styles.form}>
                <input
                    type="text"
                    placeholder="Название задачи"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    style={styles.input}
                />
                <input
                    type="text"
                    placeholder="Описание"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    style={styles.input}
                />
                <input
                    type="file"
                    onChange={(e) => setFile(e.target.files[0])}
                    style={styles.input}
                />

                {editingTask ? (
                    <>
                        <select value={status} onChange={(e) => setStatus(e.target.value)} style={styles.select}>
                            <option value="pending">Pending</option>
                            <option value="in_progress">In Progress</option>
                            <option value="done">Done</option>
                        </select>
                        <button onClick={saveTask} style={styles.button}>Сохранить</button>
                        <button onClick={cancelEdit} style={{ ...styles.button, ...styles.cancelButton }}>Отмена</button>
                    </>
                ) : (
                    <button onClick={addTask} style={styles.button}>Добавить задачу</button>
                )}
            </div>

            <ul style={styles.taskList}>
                {tasks.map((task, index) => (
                    <li key={index} style={styles.taskItem}>
                        <strong>{task.title}</strong> {task.status ? `(${task.status})` : ''} <br />
                        {task.description}
                        {task.image_url && <div><img src={task.image_url} alt="task" style={styles.taskImage} /></div>}
                        <div style={styles.taskButtons}>
                            <button onClick={() => startEdit(task)} style={styles.button}>Редактировать</button>
                            <button onClick={() => deleteTask(task.id)} style={{ ...styles.button, ...styles.cancelButton }}>Удалить</button>
                        </div>
                    </li>
                ))}
            </ul>
        </div>
    );
}

export default TaskTracker;