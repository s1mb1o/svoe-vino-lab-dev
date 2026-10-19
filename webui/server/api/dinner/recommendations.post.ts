import { handleDinner } from '../../utils/dinner'
export default defineEventHandler(event => handleDinner(event, 'recommendations'))
