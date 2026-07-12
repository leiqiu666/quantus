import { useDispatch, useSelector } from 'react-redux';
import type { RootState, AppDispatch } from './index';

/**
 * 类型安全版本的 Redux hooks，业务里**只**使用这两个，
 * 避免每次手动写泛型。
 */
export const useAppDispatch: () => AppDispatch = useDispatch;
export const useAppSelector = useSelector.withTypes<RootState>();
